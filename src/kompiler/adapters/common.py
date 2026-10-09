from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from kompiler.adapters.base import Adapter
from kompiler.errors import AdapterError
from kompiler.protocol.models import (
    OperationCapability,
    OperationLimits,
    OperationOutputDescriptor,
    OperationSemantics,
    SourceDescriptor,
)

from .utils import load_json, state_id_for_paths


def object_schema(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }


def opcap(
    operation_id: str,
    description: str,
    properties: dict[str, Any] | None = None,
    required: list[str] | None = None,
    *,
    max_items: int = 1000,
    timeout_ms: int = 30_000,
    max_bytes: int | None = None,
    record_kinds: list[str] | None = None,
    supports_reader_policy: bool = False,
    network: bool = False,
    semantic_plane: str = "source",
    requires_surface: bool = False,
    v7_native: bool = False,
) -> OperationCapability:
    return OperationCapability(
        operation_id=operation_id,
        description=description,
        input_schema=object_schema(properties or {}, required),
        output=OperationOutputDescriptor(record_kinds=record_kinds or ["record"], supports_provenance=True),
        semantics=OperationSemantics(
            read_only=True,
            deterministic=True,
            supports_reader_policy=supports_reader_policy,
            network=network,
            semantic_plane=semantic_plane,
            requires_surface=requires_surface,
            v7_native=v7_native,
        ),
        limits=OperationLimits(max_items=max_items, timeout_ms=timeout_ms, max_bytes=max_bytes),
    )


class KristalAdapterBase(Adapter):
    schema_version: str | None = None
    identity_paths: list[Path]

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self.identity_paths = []
        self._json_cache: dict[Path, tuple[int, int, Any]] = {}
        self._source_cache_sig: tuple[tuple[str, int, int], ...] | None = None
        self._source_cache: SourceDescriptor | None = None

    def _identity_signature(self) -> tuple[tuple[str, int, int], ...]:
        rows: list[tuple[str, int, int]] = []
        for p in sorted({x.resolve() for x in self.identity_paths if x.exists() and x.is_file()}, key=str):
            st = p.stat()
            try:
                rel = str(p.relative_to(self.root))
            except ValueError:
                rel = str(p)
            rows.append((rel, st.st_mtime_ns, st.st_size))
        return tuple(rows)

    def source_descriptor(self) -> SourceDescriptor:
        if not self.identity_paths:
            self.identity_paths = [p for p in self.root.glob("manifest*.json") if p.is_file()]
        sig = self._identity_signature()
        if self._source_cache is not None and sig == self._source_cache_sig:
            return self._source_cache.model_copy(deep=True)
        existing_identity_paths = [p for p in self.identity_paths if p.exists() and p.is_file()]
        state_id = state_id_for_paths(existing_identity_paths, base=self.root) if existing_identity_paths else None
        desc = SourceDescriptor(
            kristal_schema_version=self.schema_version,
            state_id=state_id,
            root_hint=self.root.name,
            integrity="local-content-hash" if state_id else "unknown",
        )
        self._source_cache_sig = sig
        self._source_cache = desc
        return desc.model_copy(deep=True)

    def health(self) -> dict[str, Any]:
        root_ok = self.root.exists() and self.root.is_dir()
        existing = [p for p in self.identity_paths if p.exists() and p.is_file()]
        missing = [
            str(p.relative_to(self.root)) if self.root in p.parents else str(p)
            for p in self.identity_paths
            if not p.exists()
        ]
        source = self.source_descriptor() if root_ok else SourceDescriptor(integrity="unknown")
        return {
            "ok": bool(root_ok and (not self.identity_paths or existing)),
            "root": str(self.root),
            "adapter_id": self.adapter_id,
            "target_id": self.target_id,
            "state_id": source.state_id,
            "missing_identity_paths": missing,
        }

    def validate_params(self, operation: str, params: dict[str, Any]) -> None:
        cap = next((x for x in self.capabilities() if x.operation_id == operation), None)
        if not cap:
            raise AdapterError("UNKNOWN_OPERATION", f"{self.target_id} does not expose operation {operation}")
        errors = sorted(Draft202012Validator(cap.input_schema).iter_errors(params), key=lambda e: list(e.path))
        if errors:
            raise AdapterError(
                "INVALID_PARAMETERS",
                f"Invalid parameters for {self.target_id}.{operation}",
                {"errors": [{"path": list(e.path), "message": e.message} for e in errors]},
            )

    def read_json(self, rel: str) -> Any:
        path = (self.root / rel).resolve()
        if self.root not in path.parents and path != self.root:
            raise AdapterError("PATH_OUTSIDE_ALLOWED_ROOT", "resolved data path escaped adapter root")
        if not path.exists():
            raise AdapterError("SOURCE_NOT_FOUND", f"missing Kristal file: {rel}")
        st = path.stat()
        cached = self._json_cache.get(path)
        if cached and cached[0] == st.st_mtime_ns and cached[1] == st.st_size:
            return cached[2]
        value = load_json(path)
        self._json_cache[path] = (st.st_mtime_ns, st.st_size, value)
        return value


def locate_root(root: Path, markers: list[str]) -> Path | None:
    root = root.resolve()
    candidates = [root]
    candidates += [p for p in root.glob("*") if p.is_dir()]
    candidates += [p for p in root.glob("*/*") if p.is_dir()]
    for c in candidates:
        if all((c / m).exists() for m in markers):
            return c
    return None


def infer_schema_version(path: Path) -> str | None:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        v = obj.get("schema_version") or obj.get("kristal_schema_version")
        return str(v) if v is not None else None
    except Exception:
        return None
