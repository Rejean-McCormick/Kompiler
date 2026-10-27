from __future__ import annotations

"""Read-only, index-first GitHub collection transport.

This is an optional reader: it does not synchronize, clone, publish or activate.
GitHub auth is delegated to an already authenticated `gh` CLI. Local checkouts use
exactly the same file/index verifier without network access. Content is fetched
only on explicit demand, pinned to a resolved commit, and checked against the
Manager's published SHA-256 read-surface inventory.
"""

import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote, urlparse

from kompiler.errors import AdapterError
from kompiler.protocol.canonical import canonical_bytes

INDEX_FORMAT = "kristal.github-collection-index/1.0"
SYNC_FORMAT = "kristal.github-sync-manifest/1.0"
SURFACE_FORMAT = "kristal.github-read-surface/1.0"
SHA = re.compile(r"^sha256:[0-9a-f]{64}$")
REPO_PART = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")
MAX_METADATA_BYTES = 8 * 1024 * 1024
MAX_FILE_BYTES = 1024 * 1024


def _sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _relative(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise AdapterError("INVALID_PATH", f"Expected a relative POSIX file path: {value!r}")
    p = PurePosixPath(value)
    if p.is_absolute() or any(t in {".", "..", ""} for t in value.split("/")):
        raise AdapterError("INVALID_PATH", f"Unsafe file path: {value!r}")
    return value


def _json_bytes(data: bytes, name: str) -> dict[str, Any]:
    try:
        doc = json.loads(data.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise AdapterError("INVALID_SOURCE", f"Invalid JSON at {name}") from exc
    if not isinstance(doc, dict):
        raise AdapterError("INVALID_SOURCE", f"Expected JSON object at {name}")
    return doc


def _check_index(index: dict[str, Any]) -> list[dict[str, Any]]:
    if index.get("format") != INDEX_FORMAT or not isinstance(index.get("kristals"), list):
        raise AdapterError("UNSUPPORTED_PROFILE", "Collection index is absent or unsupported")
    entries = index["kristals"]
    projection = {"format": INDEX_FORMAT, "kristals": entries}
    # Manager alpha.11 index digest uses Python JSON sorted-by-key UTF-8, not JCS.
    serialized = json.dumps(projection, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if index.get("count") != len(entries) or index.get("index_digest") != _sha(serialized):
        raise AdapterError("DIGEST_MISMATCH", "GitHub collection index count/digest mismatch")
    seen_paths: set[str] = set()
    seen_refs: set[str] = set()
    for item in entries:
        if not isinstance(item, dict):
            raise AdapterError("INVALID_SOURCE", "Collection index includes invalid entry")
        slug = str(item.get("slug") or "")
        rel = item.get("path")
        state_ref = item.get("state_ref")
        if not slug or "/" in slug or "\\" in slug or slug in {".", "..", "index.json"} or any(ord(ch) < 32 or ord(ch) == 127 for ch in slug) or rel != f"kristals/{slug}":
            raise AdapterError("INVALID_SOURCE", "Invalid collection slug/path pairing")
        if not isinstance(state_ref, str) or not state_ref:
            raise AdapterError("INVALID_SOURCE", "Collection entry missing state_ref")
        if rel in seen_paths or state_ref in seen_refs:
            raise AdapterError("DUPLICATE_IDENTITY", "Collection has conflicting identity or path")
        seen_paths.add(rel); seen_refs.add(state_ref)
        if item.get("entrypoint") != f"{rel}/AI_START_HERE.md" or not SHA.fullmatch(str(item.get("surface_digest") or "")):
            raise AdapterError("INVALID_SOURCE", f"Invalid entrypoint or surface digest for {slug}")
        if not isinstance(item.get("file_count"), int) or isinstance(item["file_count"], bool) or item["file_count"] < 1 or not isinstance(item.get("total_bytes"), int) or item["total_bytes"] < 0:
            raise AdapterError("INVALID_SOURCE", "Invalid collection index size metadata")
    if entries != sorted(entries, key=lambda x: (x["slug"].encode("utf-8"), x["path"].encode("utf-8"))):
        raise AdapterError("INVALID_SOURCE", "Collection index entries are not deterministic")
    return entries


def _surface_projection(manifest: dict[str, Any], objects: list[Any]) -> dict[str, Any]:
    rows = sorted(manifest["files"], key=lambda x: x["path"].encode("utf-8"))
    return {
        "format": SURFACE_FORMAT,
        "slug": manifest["slug"],
        "state_ref": manifest["state_ref"],
        "state_logical_commitment": manifest["state_logical_commitment"],
        "entrypoint": manifest["entrypoint"],
        "files": [{k: row[k] for k in ("path", "role", "size", "sha256")} for row in rows],
        "materialization_objects": objects,
    }


class CollectionReader:
    def __init__(self, source: str | Path, *, ref: str = "main") -> None:
        self.remote: str | None = None
        self.root: Path | None = None
        self.revision: str | None = None
        self._cache: dict[str, bytes] = {}
        self._manifests: dict[str, dict[str, Any]] = {}
        self._by_slug: dict[str, dict[str, Any]] = {}
        text = str(source)
        if text.startswith("https://"):
            parsed = urlparse(text)
            segments = [x for x in parsed.path.split("/") if x]
            if parsed.hostname != "github.com" or parsed.port or parsed.username or parsed.password or parsed.query or parsed.fragment or len(segments) < 2 or (len(segments) > 2 and (len(segments) < 4 or segments[2] != "tree")):
                raise AdapterError("INVALID_SOURCE", "Use https://github.com/owner/repo or /tree/<branch>")
            owner, name = segments[:2]
            name = name.removesuffix(".git")
            if not REPO_PART.fullmatch(owner) or not REPO_PART.fullmatch(name):
                raise AdapterError("INVALID_SOURCE", "Invalid GitHub owner/repository")
            self.remote = f"{owner}/{name}"
            if len(segments) > 2:
                ref = "/".join(segments[3:])
            if not ref or len(ref) > 160 or ref.startswith("-") or any(c in ref for c in ("?", "#", "\\", "\n", "\r")):
                raise AdapterError("INVALID_SOURCE", "Unsafe GitHub ref")
            gh = shutil.which("gh")
            if not gh:
                raise AdapterError("GH_UNAVAILABLE", "GitHub CLI (gh) is required to read remote collections")
            result = self._gh(f"repos/{self.remote}/commits/{quote(ref, safe='')}")
            self.revision = str(result.get("sha") or "")
            if not re.fullmatch(r"[a-f0-9]{40}", self.revision):
                raise AdapterError("INVALID_SOURCE", "Cannot resolve remote GitHub reference to immutable commit")
            self.source_uri = f"https://github.com/{self.remote}/tree/{self.revision}"
        else:
            self.root = Path(source).expanduser().resolve()
            if not self.root.is_dir():
                raise AdapterError("SOURCE_NOT_FOUND", f"Collection directory is missing: {self.root}")
            self.source_uri = str(self.root)
        self.index = _json_bytes(self._fetch("kristals/index.json", MAX_METADATA_BYTES), "kristals/index.json")
        self.entries = _check_index(self.index)
        self._by_slug = {x["slug"]: x for x in self.entries}

    @property
    def is_network(self) -> bool:
        return self.remote is not None

    def _gh(self, endpoint: str) -> dict[str, Any]:
        args = ["gh", "api", endpoint]
        kwargs: dict[str, Any] = {}
        if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        try:
            proc = subprocess.run(args, text=True, capture_output=True, timeout=25, **kwargs)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise AdapterError("GITHUB_UNAVAILABLE", f"Unable to query GitHub: {type(exc).__name__}") from exc
        if proc.returncode:
            # Never include command stderr: it may contain a private endpoint or credentials.
            raise AdapterError("GITHUB_UNAVAILABLE", "GitHub API request failed (check gh auth and repository access)")
        return _json_bytes(proc.stdout.encode("utf-8"), "GitHub API response")

    def _fetch(self, path: str, max_bytes: int = MAX_FILE_BYTES) -> bytes:
        rel = _relative(path)
        # Remote files are commit-pinned; local checkouts may change after a read.
        # Never reuse unchecked local bytes across requests.
        if self.remote and rel in self._cache:
            return self._cache[rel]
        if self.remote:
            api_path = "/".join(quote(part, safe="") for part in rel.split("/"))
            result = self._gh(f"repos/{self.remote}/contents/{api_path}?ref={self.revision}")
            if result.get("type") != "file":
                raise AdapterError("INVALID_SOURCE", "GitHub API response is not a file")
            declared_size = result.get("size")
            if not isinstance(declared_size, int) or isinstance(declared_size, bool) or declared_size < 0 or declared_size > max_bytes:
                raise AdapterError("RESOURCE_LIMIT_EXCEEDED", f"File exceeds maximum reader budget: {rel}")
            if result.get("encoding") != "base64":
                # GitHub Contents API omits inline bytes for large files. Git Blob API
                # supports larger index documents; resolve a blob SHA from the
                # immutable commit-pinned Contents API response, not a branch HEAD.
                blob_sha = result.get("sha")
                if not isinstance(blob_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", blob_sha):
                    raise AdapterError("INVALID_SOURCE", "GitHub response has no Git blob identity")
                result = self._gh(f"repos/{self.remote}/git/blobs/{blob_sha}")
                if result.get("encoding") != "base64" or result.get("size") != declared_size:
                    raise AdapterError("INVALID_SOURCE", "Git blob metadata mismatch")
            encoded = result.get("content")
            if not isinstance(encoded, str):
                raise AdapterError("INVALID_SOURCE", f"Invalid GitHub file encoding at {rel}")
            # GitHub inserts line breaks in its base64 JSON strings. Remove only
            # those transport line breaks, not arbitrary invalid characters.
            encoded = encoded.replace("\n", "").replace("\r", "")
            if len(encoded) > ((max_bytes + 2) // 3) * 4 + 4:
                raise AdapterError("RESOURCE_LIMIT_EXCEEDED", f"Encoded file exceeds reader budget: {rel}")
            try:
                data = base64.b64decode(encoded, validate=True)
            except (ValueError, TypeError, base64.binascii.Error) as exc:
                raise AdapterError("INVALID_SOURCE", f"Invalid GitHub file encoding at {rel}") from exc
            if len(data) != declared_size:
                raise AdapterError("INTEGRITY_FAILURE", f"GitHub declared file size differs from decoded bytes: {rel}")
        else:
            assert self.root is not None
            base = self.root.resolve()
            raw_target = base / Path(rel)
            if any(part.is_symlink() for part in (base / Path(*Path(rel).parts[:i]) for i in range(1, len(Path(rel).parts) + 1))):
                raise AdapterError("INVALID_PATH", "Symlink is not allowed in hosted read surface")
            target = raw_target.resolve()
            if not target.is_relative_to(base):
                raise AdapterError("INVALID_PATH", "Collection file path escapes source root")
            if not target.is_file() or target.stat().st_size > max_bytes:
                raise AdapterError("RESOURCE_LIMIT_EXCEEDED", f"File unavailable or too large: {rel}")
            with target.open("rb") as stream:
                data = stream.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise AdapterError("RESOURCE_LIMIT_EXCEEDED", f"File exceeds maximum reader budget: {rel}")
        if self.remote and len(self._cache) < 64 and len(data) < MAX_FILE_BYTES:
            self._cache[rel] = data
        return data

    def catalog(self, *, query: str = "", limit: int = 100, offset: int = 0) -> dict[str, Any]:
        term = query.casefold().strip()
        rows = [x for x in self.entries if not term or term in str(x.get("title") or "").casefold() or term in x["slug"].casefold() or term in x["state_ref"].casefold()]
        return {"repository": self.source_uri, "source_revision": self.revision, "count": len(rows), "entries": rows[max(0, offset):max(0, offset) + min(200, max(1, limit))], "index_digest": self.index["index_digest"]}

    def manifest(self, slug: str) -> dict[str, Any]:
        entry = self._by_slug.get(slug)
        if entry is None:
            raise AdapterError("UNKNOWN_KRISTAL", f"Kristal {slug!r} not found in collection index")
        if slug in self._manifests:
            return self._manifests[slug]
        base = entry["path"]
        m = _json_bytes(self._fetch(f"{base}/.kristal/sync-manifest.json", MAX_METADATA_BYTES), f"{slug} sync manifest")
        if m.get("format") != SYNC_FORMAT or m.get("read_surface_format") != SURFACE_FORMAT or m.get("slug") != slug or m.get("target_root") != base or m.get("state_ref") != entry["state_ref"] or m.get("surface_digest") != entry["surface_digest"]:
            raise AdapterError("INTEGRITY_FAILURE", f"Collection index and sync manifest disagree for {slug}")
        rows = m.get("files")
        if not isinstance(rows, list) or not rows or m.get("file_count") != len(rows):
            raise AdapterError("INVALID_SOURCE", f"Invalid sync manifest file list for {slug}")
        paths: set[str] = set()
        for row in rows:
            if not isinstance(row, dict) or not SHA.fullmatch(str(row.get("sha256") or "")) or not isinstance(row.get("size"), int) or isinstance(row["size"], bool) or row["size"] < 0 or not isinstance(row.get("role"), str) or not row["role"]:
                raise AdapterError("INVALID_SOURCE", "Malformed file metadata in sync manifest")
            rel = _relative(str(row.get("path") or ""))
            if rel in paths:
                raise AdapterError("INVALID_SOURCE", "Duplicate hosted file path")
            paths.add(rel)
        if sum(x["size"] for x in rows) != m.get("total_bytes"):
            raise AdapterError("INTEGRITY_FAILURE", "Read-surface byte total mismatch")
        if (m.get("file_count") != entry.get("file_count") or m.get("total_bytes") != entry.get("total_bytes") or
            m.get("materialization_object_count") != entry.get("materialization_object_count")):
            raise AdapterError("INTEGRITY_FAILURE", "Collection summary and sync manifest disagree")
        if not {"AI_START_HERE.md", "AI_MANIFEST.json", "ai/INDEX.json", "state/state-snapshot.json"}.issubset(paths):
            raise AdapterError("INVALID_SOURCE", "Reader entrypoint or state is not declared")
        ai_idx = self._read_declared(slug, "ai/INDEX.json", m)
        ai_doc = _json_bytes(ai_idx, "ai/INDEX.json")
        ai_manifest = _json_bytes(self._read_declared(slug, "AI_MANIFEST.json", m), "AI_MANIFEST.json")
        state = _json_bytes(self._read_declared(slug, "state/state-snapshot.json", m), "state/state-snapshot.json")
        for doc, label, commit_key in ((ai_doc, "ai/INDEX.json", "state_logical_commitment"), (ai_manifest, "AI_MANIFEST.json", "state_logical_commitment"), (state, "state/state-snapshot.json", "logical_commitment")):
            if doc.get("state_ref") != m.get("state_ref") or doc.get(commit_key) != m.get("state_logical_commitment"):
                raise AdapterError("INTEGRITY_FAILURE", f"{label} disagrees with hosted state identity")
        objects = ai_doc.get("materialization_blobs") or []
        if not isinstance(objects, list) or len(objects) != m.get("materialization_object_count"):
            raise AdapterError("INTEGRITY_FAILURE", "Materialization inventory drift")
        proj = _surface_projection(m, objects)
        if _sha(canonical_bytes(proj)) != m.get("surface_digest"):
            raise AdapterError("DIGEST_MISMATCH", f"Read-surface digest mismatch for {slug}")
        if m.get("entrypoint") != "AI_START_HERE.md" or m.get("state_logical_commitment") != entry.get("state_logical_commitment"):
            raise AdapterError("INTEGRITY_FAILURE", "Read-surface identity mismatch")
        for item in ai_doc.get("files") or []:
            ref = next((r for r in rows if r["path"] == item.get("path")), None)
            if ref is None or (item.get("sha256") and item["sha256"] != ref["sha256"]):
                raise AdapterError("INTEGRITY_FAILURE", "AI index references content outside verified read surface")
        self._manifests[slug] = m
        return m

    def _read_declared(self, slug: str, rel: str, manifest: dict[str, Any]) -> bytes:
        row = next((x for x in manifest["files"] if x["path"] == rel), None)
        if row is None:
            raise AdapterError("UNDECLARED_RESOURCE", "Requested file is not in the verified read-surface manifest")
        if row["size"] > MAX_FILE_BYTES:
            raise AdapterError("RESOURCE_LIMIT_EXCEEDED", "Large materialization bytes must use their separate transport")
        data = self._fetch(f"kristals/{slug}/{_relative(rel)}")
        if len(data) != row["size"] or _sha(data) != row["sha256"]:
            raise AdapterError("DIGEST_MISMATCH", f"Hosted bytes differ from declared read surface: {slug}/{rel}")
        return data

    def read(self, slug: str, path: str) -> dict[str, Any]:
        manifest = self.manifest(slug)
        rel = _relative(path)
        data = self._read_declared(slug, rel, manifest)
        if b"\0" in data:
            raise AdapterError("NON_TEXT_RESOURCE", "Binary resources are not compiled as text")
        try:
            txt = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AdapterError("NON_TEXT_RESOURCE", "Resource is not UTF-8 text") from exc
        return {"slug": slug, "path": rel, "github_path": f"kristals/{slug}/{rel}", "content": txt, "sha256": _sha(data), "state_ref": manifest["state_ref"], "surface_digest": manifest["surface_digest"], "state_logical_commitment": manifest["state_logical_commitment"], "source_revision": self.revision, "source": self.source_uri}

    def reading_map(self, slug: str, *, limit: int = 100) -> dict[str, Any]:
        m = self.manifest(slug)
        return {"slug": slug, "state_ref": m["state_ref"], "surface_digest": m["surface_digest"], "state_logical_commitment": m["state_logical_commitment"], "source_revision": self.revision, "entrypoint": f"kristals/{slug}/AI_START_HERE.md", "files": m["files"][:min(500, max(1, limit))], "file_count": m["file_count"], "materialization_object_count": m["materialization_object_count"], "source": self.source_uri}
