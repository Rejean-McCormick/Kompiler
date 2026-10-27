"""Opt-in, local-only v11 Context Pack reader via the pinned Integration Pack.

Canonical graph, Framework scripts and lexical sources are never written by Kompiler.
No inference of authority, public authorization, or equivalence from lexical terms.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from kompiler.adapters.base import Adapter, AdapterContext, AdapterResult
from kompiler.adapters.common import opcap
from kompiler.adapters.manifest import AdapterManifest
from kompiler.errors import AdapterError
from kompiler.protocol.models import OperationCapability, SourceDescriptor

PACK_TOOL_SHA256 = "6c94ffd8f8f9619d17afcd0548037d95fda40e93b6ade6bc43e36d1edd27bba1"
PACK_PIN_SHA256 = "cdb7df8e63ea609c3cda368de012e210f7a07e0d4d86c315ac0059ae996a030e"
PROFILE = "kristal.integration.read-view/v11.0-draft.1"
ID = re.compile(r"^(?:KQ|KP|KA|KS)[1-9][0-9]*$")
LOCALE = re.compile(r"^[a-zA-Z]{2,8}(?:-[a-zA-Z0-9]{1,8})*$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
MAX_VIEW_BYTES = 8 * 1024 * 1024
MAX_RECORDS = 1000


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for data in iter(lambda: f.read(1024 * 1024), b""):
            h.update(data)
    return h.hexdigest()


def _required_file(root: Path, name: str) -> Path:
    path = Path(name)
    if path.is_absolute() or not path.parts or any(part in {"..", "."} for part in path.parts):
        raise AdapterError("INVALID_V11_CONFIG", f"Unsafe relative source path: {name}")
    full = (root / path).resolve()
    if not full.is_relative_to(root) or not full.is_file():
        raise AdapterError("INVALID_V11_CONFIG", f"Missing or escaping source file: {name}")
    return full


def _pinned_pack(pack: Path) -> Path:
    script = pack / "tools" / "v11_integration.py"
    pin = pack / "contracts" / "v11-framework-pin.json"
    for path, expected in ((script, PACK_TOOL_SHA256), (pin, PACK_PIN_SHA256)):
        if not path.is_file() or _sha(path) != expected:
            raise AdapterError("UNTRUSTED_V11_PACK", "Integration Pack script/pin differs from reviewed 0.3.0-alpha.1")
    return script


def _view_guard(view: Any, *, locale: str, namespace: str, paths: dict[str, Path]) -> dict[str, Any]:
    """Check the generated envelope and its exact provenance before adaptation."""
    if not isinstance(view, dict) or view.get("profile") != PROFILE or view.get("derived_only") is not True:
        raise AdapterError("INVALID_V11_VIEW", "Noncanonical/unsupported v11 view")
    source = view.get("source")
    if not isinstance(source, dict) or source.get("namespace_id") != namespace or source.get("framework_version") != "11.0.0-draft.4":
        raise AdapterError("INVALID_V11_VIEW", "Untrusted view source namespace/framework")
    for field, name in (("graph_sha256", "graph"), ("registry_sha256", "registry"), ("crosswalk_sha256", "crosswalk"), ("catalog_sha256", "catalog")):
        if not DIGEST.fullmatch(str(source.get(field, ""))) or source[field] != _sha(paths[name]):
            raise AdapterError("INVALID_V11_VIEW", "View digest does not match its source bytes")
    if not isinstance(source.get("graph_id"), str) or not source["graph_id"] or view.get("requested_locale") != locale:
        raise AdapterError("INVALID_V11_VIEW", "View graph/locale mismatch")
    presentation, assertions, counts = view.get("presentation"), view.get("assertions"), view.get("coverage_counts")
    if not isinstance(presentation, list) or not isinstance(assertions, list) or not isinstance(counts, dict):
        raise AdapterError("INVALID_V11_VIEW", "Missing read-view inventories")
    actual = {"direct": 0, "fallback": 0, "missing": 0}
    known: set[str] = set()
    for entry in presentation:
        if not isinstance(entry, dict) or entry.get("kind") not in {"entity", "property"}:
            raise AdapterError("INVALID_V11_VIEW", "Invalid lexical inventory entry")
        ref = entry.get("semantic_id")
        prefix = "KQ" if entry["kind"] == "entity" else "KP"
        if not isinstance(ref, str) or not ID.fullmatch(ref) or not ref.startswith(prefix) or ref in known:
            raise AdapterError("INVALID_V11_VIEW", "Invalid/duplicate canonical lexical reference")
        known.add(ref)
        lex = entry.get("lexical")
        if not isinstance(lex, dict) or lex.get("status") not in actual:
            raise AdapterError("INVALID_V11_VIEW", "Unknown lexical status")
        status = lex["status"]
        if status == "missing":
            if "term" in lex:
                raise AdapterError("INVALID_V11_VIEW", "Missing label may not invent a term")
        elif not all(isinstance(lex.get(k), str) and lex[k] for k in ("term", "layer_id", "effective_locale")):
            raise AdapterError("INVALID_V11_VIEW", "Lexical term lacks provenance")
        elif (status == "direct") != (lex["effective_locale"] == locale):
            raise AdapterError("INVALID_V11_VIEW", "Incorrect direct/fallback attribution")
        external = entry.get("accepted_external_exact")
        if external is not None:
            ext_prefix = "Q" if prefix == "KQ" else "P"
            if not isinstance(external, dict) or external.get("system") != "wikidata" or not re.fullmatch(rf"{ext_prefix}[1-9][0-9]*", str(external.get("id", ""))):
                raise AdapterError("INVALID_V11_VIEW", "Invalid exact crosswalk")
        actual[status] += 1
    if actual != counts:
        raise AdapterError("INVALID_V11_VIEW", "Lexical coverage summary mismatch")
    assertions_seen = set()
    for a in assertions:
        if not isinstance(a, dict) or not all(isinstance(a.get(k), str) for k in ("id", "subject", "predicate")):
            raise AdapterError("INVALID_V11_VIEW", "Invalid v11 assertion")
        if (not a["id"].startswith("KA") or not ID.fullmatch(a["id"])
                or a["id"] in assertions_seen or not a["subject"].startswith("KQ")
                or not a["predicate"].startswith("KP") or a["subject"] not in known
                or a["predicate"] not in known):
            raise AdapterError("INVALID_V11_VIEW", "Unresolved/duplicate assertion identity")
        assertions_seen.add(a["id"])
        obj = a.get("object")
        if not isinstance(obj, dict) or obj.get("kind") not in {"entity", "literal"}:
            raise AdapterError("INVALID_V11_VIEW", "Invalid assertion object")
        if obj["kind"] == "entity" and obj.get("id") not in known:
            raise AdapterError("INVALID_V11_VIEW", "Unresolved assertion object entity")
        if obj["kind"] == "literal" and ("value" not in obj or obj.get("datatype") not in {"string", "boolean", "integer", "number", "date", "dateTime", "uri"}):
            raise AdapterError("INVALID_V11_VIEW", "Invalid typed literal")
        if not isinstance(a.get("sources"), list) or any(not isinstance(s, str) or not s.startswith("KS") or not ID.fullmatch(s) for s in a["sources"]):
            raise AdapterError("INVALID_V11_VIEW", "Invalid source reference")
        if "qualifiers" in a:
            if not isinstance(a["qualifiers"], list):
                raise AdapterError("INVALID_V11_VIEW", "Malformed qualifiers")
            for q in a["qualifiers"]:
                if (not isinstance(q, dict) or q.get("predicate") not in known
                        or not str(q["predicate"]).startswith("KP") or not isinstance(q.get("object"), dict)
                        or q["object"].get("kind") not in {"entity", "literal"}):
                    raise AdapterError("INVALID_V11_VIEW", "Invalid qualifier")
                if (q["object"]["kind"] == "entity" and q["object"].get("id") not in known):
                    raise AdapterError("INVALID_V11_VIEW", "Unresolved qualifier entity")
                if (q["object"]["kind"] == "literal" and
                        ("value" not in q["object"] or q["object"].get("datatype") not in
                         {"string", "boolean", "integer", "number", "date", "dateTime", "uri"})):
                    raise AdapterError("INVALID_V11_VIEW", "Invalid qualifier literal")
    return view


class KristalV11ReadViewAdapter(Adapter):
    adapter_id = "kristal-v11-read-view"
    adapter_version = "0.1.0"
    kind = "kristal"

    def __init__(self, manifest: AdapterManifest):
        self.root = manifest.root
        options = manifest.options
        if options.get("local_read_approved") is not True:
            raise AdapterError("V11_APPROVAL_REQUIRED", "Enable local_read_approved explicitly for a trusted local source")
        if not self.root.is_dir():
            raise AdapterError("INVALID_V11_CONFIG", "v11 source root is missing")
        self.paths = {key: _required_file(self.root, str(options.get(key, ""))) for key in ("registry", "graph", "crosswalk", "catalog")}
        if not options.get("framework_root") or not options.get("integration_pack_root"):
            raise AdapterError("INVALID_V11_CONFIG", "Explicit Framework and Integration Pack roots required")
        self.framework = Path(str(options["framework_root"])).expanduser().resolve()
        self.pack = Path(str(options["integration_pack_root"])).expanduser().resolve()
        self.script = _pinned_pack(self.pack)
        if not (self.framework / "VERSION").is_file() or (self.framework / "VERSION").read_text("utf-8").strip() != "11.0.0-draft.4":
            raise AdapterError("INVALID_V11_CONFIG", "Framework 11.0.0-draft.4 checkout required")
        self.target_id = manifest.target_id
        graph = json.loads(self.paths["graph"].read_text(encoding="utf-8"))
        self.namespace = graph.get("namespace_id") if isinstance(graph, dict) else None
        if not isinstance(self.namespace, str) or not self.namespace:
            raise AdapterError("INVALID_V11_CONFIG", "Missing canonical namespace")
        # Do not preload terms, views, or inferences into a persistent cache.

    def capabilities(self) -> list[OperationCapability]:
        return [opcap("read", "Read selected v11 identifiers/assertions as noncanonical local context (no rights conferred).", {
            "locale": {"type": "string", "pattern": LOCALE.pattern},
            "semantic_ids": {"type": "array", "items": {"type": "string", "pattern": ID.pattern}, "uniqueItems": True, "maxItems": MAX_RECORDS},
        }, required=["locale", "semantic_ids"], max_items=MAX_RECORDS, timeout_ms=60_000,
        record_kinds=["kristal_v11_identity", "kristal_v11_assertion", "kristal_v11_source_ref"], network=False)]

    def source_descriptor(self) -> SourceDescriptor:
        # Digest is recomputed so changes to the canonical source invalidate cache ids.
        digests = {k: _sha(p) for k, p in self.paths.items()}
        # Cache and capability fingerprints must vary on lexical/crosswalk edits too.
        state_digest = hashlib.sha256(json.dumps(digests, sort_keys=True).encode("utf-8")).hexdigest()
        return SourceDescriptor(kristal_schema_version="11.0.0-draft.4", state_id=self.namespace,
            snapshot_id=state_digest, contract_family=PROFILE,
            integrity="pinned-framework-validated-per-execution",
            source_sha256=digests, derived_only=True, local_only=True)

    def health(self) -> dict[str, Any]:
        return {"ok": all(p.is_file() for p in self.paths.values()) and self.script.is_file(),
                "adapter_id": self.adapter_id, "target_id": self.target_id, "local_only": True}

    def _generate(self, locale: str, timeout_ms: int) -> dict[str, Any]:
        # A new temp file outside canonical sources; the pinned tool creates it exclusively.
        with tempfile.TemporaryDirectory(prefix="kompiler-v11-read-") as temp:
            output = Path(temp) / "view.json"
            argv = [sys.executable, "-I", str(self.script), "view", "--framework", str(self.framework)]
            for key in ("registry", "graph", "crosswalk", "catalog"):
                argv += ["--" + key, str(self.paths[key])]
            argv += ["--locale", locale, "--out", str(output)]
            try:
                run = subprocess.run(argv, capture_output=True, timeout=max(1, min(timeout_ms, 60_000)) / 1000,
                    check=False, cwd=str(self.pack))
            except subprocess.TimeoutExpired as exc:
                raise AdapterError("TIMEOUT", "Pinned v11 read-view validation timed out") from exc
            if run.returncode != 0:
                raise AdapterError("INVALID_V11_SOURCE", "Pinned Framework/Pack rejected v11 sources", {"exit_code": run.returncode})
            if not output.is_file() or output.stat().st_size > MAX_VIEW_BYTES:
                raise AdapterError("RESOURCE_LIMIT_EXCEEDED", "Derived v11 view exceeds local limits")
            try:
                view = json.loads(output.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise AdapterError("INVALID_V11_VIEW", "Invalid read-view JSON") from exc
        return _view_guard(view, locale=locale, namespace=self.namespace, paths=self.paths)

    async def execute(self, operation: str, params: dict[str, Any], context: AdapterContext) -> AdapterResult:
        if operation != "read":
            raise AdapterError("UNKNOWN_OPERATION", "v11 adapter only supports read")
        locale, ids = params.get("locale"), params.get("semantic_ids")
        if not isinstance(locale, str) or not LOCALE.fullmatch(locale) or not isinstance(ids, list) or not ids or len(ids) > MAX_RECORDS or any(not isinstance(i, str) or not ID.fullmatch(i) for i in ids) or len(ids) != len(set(ids)):
            raise AdapterError("INVALID_PARAMETERS", "A valid locale and explicit unique semantic_ids are required")
        _pinned_pack(self.pack)  # fail closed on tool drift after adapter registration
        view = self._generate(locale, context.timeout_ms)
        chosen = set(ids)
        lexicon = {r["semantic_id"]: r for r in view["presentation"]}
        assertion_map = {a["id"]: a for a in view["assertions"]}
        declared_sources = {s for a in view["assertions"] for s in a["sources"]}
        for item in chosen:
            if item not in lexicon and item not in assertion_map and item not in declared_sources:
                raise AdapterError("UNKNOWN_V11_ID", "Requested identifier is not in the reviewed v11 graph")
        records: list[dict[str, Any]] = []
        sources = set()
        for item in view["presentation"]:
            if item["semantic_id"] not in chosen:
                continue
            records.append({"kind": "kristal_v11_identity", "record_id": item["semantic_id"],
                "semantic_id": item["semantic_id"], "semantic_role": "entity" if item["kind"] == "entity" else "record",
                "canonical_kind": item["kind"], "lexical": item["lexical"],
                "accepted_external_exact": item.get("accepted_external_exact"),
                "namespace_id": self.namespace, "locale": locale, "derived_only": True})
        for a in view["assertions"]:
            if a["id"] not in chosen:
                continue
            sources.update(a["sources"])
            record = {"kind": "kristal_v11_assertion", "record_id": a["id"], "semantic_id": a["id"],
                "namespace_id": self.namespace, "subject_ref": a["subject"],
                "predicate_ref": a["predicate"], "object": a["object"],
                "canonical_sources": a["sources"], "qualifiers": a.get("qualifiers", []),
                "derived_only": True,
                "evidence_refs": [{"source_ref": {"id": f"{self.namespace}:{s}"}} for s in a["sources"]]}
            if a["object"]["kind"] == "entity":
                record["object_ref"] = a["object"]["id"]
            records.append(record)
        for source_id in sorted(chosen & declared_sources):
            sources.add(source_id)
            records.append({"kind": "kristal_v11_source_ref", "record_id": source_id,
                "semantic_id": source_id, "namespace_id": self.namespace,
                "derived_only": True, "source_locator_verified": False})
        limit = min(MAX_RECORDS, context.max_items or MAX_RECORDS)
        if len(records) > limit:
            raise AdapterError("RESOURCE_LIMIT_EXCEEDED", "v11 selection exceeds max_items; narrow semantic_ids")
        src = view["source"]
        return AdapterResult(items=records, raw_item_count=len(records),
            sources=[{"source_id": f"{self.namespace}:{s}", "title": f"v11 source {s}", "target_id": self.target_id} for s in sorted(sources)],
            metadata={"view_profile": PROFILE, "derived_only": True, "namespace_id": self.namespace,
                "graph_id": src["graph_id"], "requested_locale": locale, "coverage_counts": view["coverage_counts"],
                "framework_version": src["framework_version"],
                "canonical_source_digests": {key: src[key] for key in ("graph_sha256", "registry_sha256", "crosswalk_sha256", "catalog_sha256")},
                "publication_authorized": False})
