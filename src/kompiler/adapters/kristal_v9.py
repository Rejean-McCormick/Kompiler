from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from kompiler.adapters.base import Adapter, AdapterContext, AdapterResult
from kompiler.adapters.common import opcap
from kompiler.errors import AdapterError
from kompiler.kristal_standard import get_standard
from kompiler.protocol.models import OperationCapability, SourceDescriptor

V9_STATE = "kristal_state_snapshot"
LOCAL_WORKSPACE_FILE = "kristal.workspace.json"


@dataclass(frozen=True, slots=True)
class V9StateCandidate:
    path: Path
    surface: str


def _json_object(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return value if isinstance(value, dict) else None


def _is_v9_state(path: Path) -> bool:
    value = _json_object(path)
    return bool(
        value
        and value.get("schema_version") == "9.0"
        and value.get("artifact_type") == V9_STATE
    )


def _workspace_root_for(path: Path) -> Path | None:
    """Find the nearest Local Kristal root without executing workspace tools."""
    start = path if path.is_dir() else path.parent
    for candidate in (start, *start.parents):
        if (candidate / LOCAL_WORKSPACE_FILE).is_file():
            return candidate
    return None


def _release_candidates(root: Path) -> list[V9StateCandidate]:
    release_root = root / "release" / "v9" / "states"
    if not release_root.is_dir():
        return []
    # Local Kit releases are content-addressed nested directories. Do not infer
    # "latest" from mtime or a digest's lexical ordering. Multiple historical
    # releases therefore remain ambiguous unless the caller names one exactly.
    paths = sorted(
        (p.resolve() for p in release_root.glob("**/state-snapshot.json") if p.is_file()),
        key=lambda p: p.as_posix().encode("utf-8"),
    )
    return [V9StateCandidate(p, "release-v9") for p in paths if _is_v9_state(p)]


def find_v9_state_candidates(root: str | Path) -> list[V9StateCandidate]:
    """Return readable v9 state surfaces in explicit selection order.

    For a Local Kit workspace, the current build is authoritative for *working
    local discovery*. The optional AI mirror follows, then legacy surfaces.
    Historical release states are only auto-selected when exactly one exists;
    callers that want a specific historical release should pass its directory or
    state-snapshot.json explicitly.
    """
    p = Path(root).expanduser().resolve()
    if p.is_file():
        return [V9StateCandidate(p, "explicit-file")] if _is_v9_state(p) else []

    if not p.is_dir():
        return []

    workspace = _workspace_root_for(p)
    candidates: list[V9StateCandidate] = []

    if workspace == p:
        ordered = [
            ("build-v9", p / "build" / "v9" / "state-snapshot.json"),
            ("portable-ai-state", p / "state" / "state-snapshot.json"),
            ("legacy-dot-kristal-v9", p / ".kristal" / "v9" / "state-snapshot.json"),
            ("legacy-root", p / "state-snapshot.json"),
        ]
        for surface, path in ordered:
            if path.is_file() and _is_v9_state(path):
                candidates.append(V9StateCandidate(path.resolve(), surface))
        releases = _release_candidates(p)
        if len(releases) == 1:
            candidates.extend(releases)
        return candidates

    # When the caller points directly at a release/bundle directory, its local
    # state-snapshot wins over any ancestor workspace build.
    direct = p / "state-snapshot.json"
    if direct.is_file() and _is_v9_state(direct):
        candidates.append(V9StateCandidate(direct.resolve(), "explicit-directory"))

    # Legacy reference layout remains readable for compatibility.
    legacy = p / ".kristal" / "v9" / "state-snapshot.json"
    if legacy.is_file() and _is_v9_state(legacy):
        candidates.append(V9StateCandidate(legacy.resolve(), "legacy-dot-kristal-v9"))
    for path in sorted(p.glob(".kristal/v9/*.state-snapshot.json"), key=lambda x: x.name.encode("utf-8")):
        if path.is_file() and _is_v9_state(path):
            candidates.append(V9StateCandidate(path.resolve(), "legacy-dot-kristal-v9"))

    # If a subdirectory of a Local Kristal was supplied and no direct state was
    # found, fall back to the workspace's current working state.
    if not candidates and workspace is not None:
        return find_v9_state_candidates(workspace)
    return candidates


def find_v9_state(root: str | Path) -> Path | None:
    candidates = find_v9_state_candidates(root)
    return candidates[0].path if candidates else None


def _state_surface(root: str | Path, state_path: Path) -> str:
    for candidate in find_v9_state_candidates(root):
        if candidate.path == state_path.resolve():
            return candidate.surface
    return "explicit"


def target_id_for_v9(path: Path) -> str:
    value = _json_object(path) or {}
    ref = str(value.get("state_ref") or "")
    workspace = _workspace_root_for(path)
    fallback = workspace.name if workspace else path.parent.name
    return f"KristalV9:{ref or fallback}"


def _workspace_metadata(workspace: Path | None) -> dict[str, Any]:
    if workspace is None:
        return {}
    value = _json_object(workspace / LOCAL_WORKSPACE_FILE) or {}
    return {
        "workspace_root": str(workspace),
        "workspace_format": value.get("format"),
        "workspace_slug": value.get("slug"),
        "workspace_title": value.get("title"),
    }


class KristalV9StateAdapter(Adapter):
    adapter_id = "kristal-v9-state"
    adapter_version = "1.1.0"
    kind = "kristal"

    def __init__(self, root: str | Path, target_id: str | None = None):
        p = find_v9_state(root)
        if p is None:
            raise AdapterError("SOURCE_NOT_FOUND", f"no Kristal v9 state snapshot found at {root}")
        self.requested_root = Path(root).expanduser().resolve()
        self.state_path = p
        self.workspace_root = _workspace_root_for(p)
        self.surface = _state_surface(root, p)
        self.root = self.workspace_root or p.parent
        self.target_id = target_id or target_id_for_v9(p)
        self._state = self._load()

    def _validate(self, d: dict[str, Any]) -> None:
        schema_path = get_standard().schema_for_artifact(str(d.get("artifact_type") or ""))
        if schema_path is None:
            raise AdapterError("KRISTAL_V9_SCHEMA_MISSING", f"no Standard schema for {d.get('artifact_type')}")
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        errs = sorted(Draft202012Validator(schema).iter_errors(d), key=lambda e: list(e.absolute_path))
        if errs:
            raise AdapterError(
                "INVALID_V9_ARTIFACT",
                "v9 artifact failed Standard schema",
                {"errors": [{"path": list(e.absolute_path), "message": e.message} for e in errs[:32]]},
            )

    def _load(self) -> dict[str, Any]:
        try:
            d = json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise AdapterError("INVALID_SOURCE", f"cannot parse v9 state: {exc}") from exc
        self._validate(d)
        return d

    def _artifact_dirs(self) -> list[Path]:
        dirs: list[Path] = []
        # Exact release/bundle artifacts must stay coupled to that release.
        release_artifacts = self.state_path.parent / "artifacts"
        if release_artifacts.is_dir():
            dirs.append(release_artifacts)

        if self.workspace_root is not None and self.surface in {
            "build-v9",
            "portable-ai-state",
            "legacy-dot-kristal-v9",
            "legacy-root",
        }:
            current = self.workspace_root / "build" / "v9" / "artifacts"
            if current.is_dir():
                dirs.append(current)

        # Legacy layouts sometimes colocated logical artifacts with the state.
        dirs.append(self.state_path.parent)
        out: list[Path] = []
        for d in dirs:
            if d not in out:
                out.append(d)
        return out

    def _local_artifacts(self) -> list[tuple[Path, dict[str, Any]]]:
        out: list[tuple[Path, dict[str, Any]]] = []
        seen: set[Path] = set()
        for directory in self._artifact_dirs():
            for p in sorted(directory.glob("*.json"), key=lambda x: x.name.encode("utf-8")):
                p = p.resolve()
                if p == self.state_path.resolve() or p in seen:
                    continue
                seen.add(p)
                d = _json_object(p)
                if not d or d.get("artifact_type") != "kristal_logical_artifact":
                    continue
                self._validate(d)
                out.append((p, d))
        return out

    def source_descriptor(self) -> SourceDescriptor:
        c = self._state.get("logical_commitment") or {}
        meta = _workspace_metadata(self.workspace_root)
        root_hint: str
        if self.workspace_root is not None:
            try:
                root_hint = self.state_path.relative_to(self.workspace_root).as_posix()
            except ValueError:
                root_hint = self.state_path.name
        else:
            root_hint = self.state_path.name
        return SourceDescriptor(
            kristal_schema_version="9.0",
            state_id=self._state.get("state_ref"),
            snapshot_id=c.get("digest"),
            contract_family="kristal.state",
            root_hint=root_hint,
            integrity="declared-v9-logical-commitment",
            local_surface=self.surface,
            **{k: v for k, v in meta.items() if v is not None},
        )

    def health(self) -> dict[str, Any]:
        candidates = find_v9_state_candidates(self.workspace_root or self.requested_root)
        return {
            "ok": True,
            "adapter_id": self.adapter_id,
            "target_id": self.target_id,
            "state_ref": self._state.get("state_ref"),
            "logical_commitment": self._state.get("logical_commitment"),
            "members": len(self._state.get("members") or []),
            "references": len(self._state.get("references") or []),
            "local_surface": self.surface,
            "state_path": str(self.state_path),
            "workspace_root": str(self.workspace_root) if self.workspace_root else None,
            "available_surfaces": [
                {"surface": c.surface, "path": str(c.path)} for c in candidates
            ],
        }

    def capabilities(self) -> list[OperationCapability]:
        return [
            opcap(
                "state",
                "Read v9 State Snapshot membership and pinned references.",
                {},
                max_items=1,
                record_kinds=["kristal_state_snapshot"],
            ),
            opcap(
                "artifacts",
                "Read local v9 Logical Artifacts without mutating their native payload.",
                {},
                max_items=1000,
                record_kinds=["kristal_logical_artifact"],
            ),
        ]

    async def execute(self, operation: str, params: dict[str, Any], context: AdapterContext) -> AdapterResult:
        if operation == "state":
            return AdapterResult(
                items=[{"kind": "kristal_state_snapshot", **self._state}],
                metadata={
                    "source_bytes_preserved": True,
                    "local_surface": self.surface,
                    "state_path": str(self.state_path),
                },
                raw_item_count=1,
            )
        if operation == "artifacts":
            artifacts = self._local_artifacts()
            rows = [
                {
                    "kind": "kristal_logical_artifact",
                    "source_file": (
                        p.relative_to(self.workspace_root).as_posix()
                        if self.workspace_root and p.is_relative_to(self.workspace_root)
                        else p.name
                    ),
                    **d,
                }
                for p, d in artifacts
            ]
            limit = context.max_items or len(rows)
            return AdapterResult(
                items=rows[:limit],
                raw_item_count=len(rows),
                truncated=len(rows) > limit,
                metadata={
                    "source_bytes_preserved": True,
                    "local_surface": self.surface,
                },
            )
        raise AdapterError("UNKNOWN_OPERATION", f"{self.target_id} does not expose operation {operation}")
