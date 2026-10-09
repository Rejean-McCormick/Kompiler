from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from kompiler.adapters.base import Adapter, AdapterContext, AdapterResult
from kompiler.adapters.common import opcap
from kompiler.errors import AdapterError
from kompiler.protocol.models import OperationCapability, SourceDescriptor
from kompiler.kristal_standard import get_standard


def _looks_like_v6_state(path: Path) -> bool:
    if not path.is_file() or path.suffix.lower() != ".json":
        return False
    try:
        with path.open("r", encoding="utf-8") as f:
            value = json.load(f)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    return (
        isinstance(value, dict)
        and value.get("schema_version") == "6.0"
        and value.get("artifact_type") == "kristal_state"
    )


def find_v6_state(root: str | Path) -> Path | None:
    """Find one portable v6 state without recursively crawling an arbitrary tree.

    Repository discovery already walks directories with a bounded depth, so this helper
    only inspects the supplied directory and a few conventional one-level locations.
    """

    p = Path(root).expanduser().resolve()
    if p.is_file():
        return p if _looks_like_v6_state(p) else None
    if not p.is_dir():
        return None

    preferred = [
        p / "kristal-state.json",
        p / "kristal_state.json",
        p / "state.json",
        p / "current-state.json",
    ]
    candidates: list[Path] = preferred
    for pattern in (
        "*.json",
        "state/*.json",
        "states/*.json",
        "projections/*.json",
        "corpus/*.json",
    ):
        candidates.extend(sorted(p.glob(pattern)))

    seen: set[Path] = set()
    # Keep detection bounded even in directories containing many JSON shards.
    for candidate in candidates[:128]:
        try:
            candidate = candidate.resolve()
        except OSError:
            continue
        if candidate in seen:
            continue
        seen.add(candidate)
        if _looks_like_v6_state(candidate):
            return candidate
    return None


def target_id_for_state(path: Path) -> str:
    stem = path.stem
    if stem in {"kristal-state", "kristal_state", "state", "current-state"}:
        stem = path.parent.name
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in stem).strip("-")
    return f"KristalState:{safe or 'state'}"


class KristalV6StateAdapter(Adapter):
    """Generic read-only adapter for any valid portable `kristal_state/6.0` artifact.

    The adapter validates but never rewrites source bytes and never computes a replacement
    v6 `state_id`. A local byte snapshot is tracked separately when the source did not
    declare a state identity.
    """

    adapter_id = "kristal-v6-state"
    adapter_version = "1.0.0"
    kind = "kristal"

    def __init__(self, root: str | Path, target_id: str | None = None) -> None:
        state_path = find_v6_state(root)
        if state_path is None:
            raise AdapterError("SOURCE_NOT_FOUND", f"no kristal_state/6.0 artifact found at {root}")
        self.state_path = state_path
        self.root = state_path.parent
        self.target_id = target_id or target_id_for_state(state_path)
        self._signature: tuple[int, int] | None = None
        self._state: dict[str, Any] | None = None
        self._raw_sha256: str | None = None
        self._load()

    def _load(self) -> dict[str, Any]:
        try:
            st = self.state_path.stat()
        except OSError as exc:
            raise AdapterError("SOURCE_NOT_FOUND", f"missing v6 state {self.state_path}") from exc
        signature = (st.st_mtime_ns, st.st_size)
        if self._state is not None and signature == self._signature:
            return self._state
        try:
            raw = self.state_path.read_bytes()
            value = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise AdapterError("INVALID_SOURCE", f"cannot parse v6 state {self.state_path}: {exc}") from exc
        if not isinstance(value, dict):
            raise AdapterError("INVALID_SOURCE", "v6 state must be a JSON object")
        schema = json.loads(get_standard().portable_state_schema.read_text(encoding="utf-8"))
        errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda e: list(e.absolute_path))
        if errors:
            raise AdapterError(
                "INVALID_V6_STATE",
                f"source failed kristal_state/6.0 validation: {self.state_path}",
                {"errors": [{"path": list(e.absolute_path), "message": e.message} for e in errors[:32]]},
            )
        self._state = value
        self._signature = signature
        self._raw_sha256 = hashlib.sha256(raw).hexdigest()
        return value

    def source_descriptor(self) -> SourceDescriptor:
        state = self._load()
        declared_state_id = state.get("state_id")
        raw_snapshot = f"file-sha256:{self._raw_sha256}" if self._raw_sha256 else None
        return SourceDescriptor(
            kristal_schema_version="6.0",
            state_id=str(declared_state_id) if declared_state_id else None,
            snapshot_id=str(declared_state_id) if declared_state_id else raw_snapshot,
            contract_family="kristal_state",
            canonicalization_profile=state.get("canonicalization_profile"),
            root_hint=self.state_path.name,
            integrity="declared-v6-state-id" if declared_state_id else "local-byte-snapshot",
        )

    def health(self) -> dict[str, Any]:
        try:
            state = self._load()
            source = self.source_descriptor()
            return {
                "ok": True,
                "adapter_id": self.adapter_id,
                "target_id": self.target_id,
                "state_path": str(self.state_path),
                "state_id": source.state_id,
                "snapshot_id": source.snapshot_id,
                "assertion_count": len(state.get("assertions", [])),
            }
        except Exception as exc:
            return {
                "ok": False,
                "adapter_id": self.adapter_id,
                "target_id": self.target_id,
                "state_path": str(self.state_path),
                "error": str(exc),
            }

    def capabilities(self) -> list[OperationCapability]:
        string = {"type": "string", "minLength": 1}
        array_string = {"type": "array", "items": string}
        return [
            opcap(
                "assertions",
                "Read unchanged v6 assertions with exact source-state filters.",
                {
                    "assertion_ids": array_string,
                    "statuses": array_string,
                    "record_roles": array_string,
                    "predicate": string,
                    "subject_id": string,
                    "object_id": string,
                },
                max_items=10000,
                record_kinds=["assertion"],
            ),
            opcap(
                "meta",
                "Read v6 state metadata without returning the assertion corpus.",
                {},
                max_items=1,
                record_kinds=["kristal_state_meta"],
            ),
        ]

    @staticmethod
    def _statement_ref(value: Any) -> str | None:
        if isinstance(value, str):
            return value
        if not isinstance(value, dict):
            return None
        for key in ("id", "external_id", "referent_id", "value"):
            candidate = value.get(key)
            if isinstance(candidate, (str, int, float, bool)):
                return str(candidate)
        return None

    async def execute(self, operation: str, params: dict[str, Any], context: AdapterContext) -> AdapterResult:
        state = self._load()
        if operation == "meta":
            meta = {k: v for k, v in state.items() if k not in {"assertions", "provenance"}}
            meta.update(
                {
                    "kind": "kristal_state_meta",
                    "assertion_count": len(state.get("assertions", [])),
                    "provenance_count": len(state.get("provenance", [])),
                }
            )
            return AdapterResult(items=[meta], raw_item_count=1)
        if operation != "assertions":
            raise AdapterError("UNKNOWN_OPERATION", f"{self.target_id} does not expose operation {operation}")

        rows = [x for x in state.get("assertions", []) if isinstance(x, dict)]
        ids = set(params.get("assertion_ids") or [])
        statuses = set(params.get("statuses") or [])
        roles = set(params.get("record_roles") or [])
        predicate = params.get("predicate")
        subject_id = params.get("subject_id")
        object_id = params.get("object_id")

        if ids:
            rows = [x for x in rows if x.get("assertion_id") in ids]
        if statuses:
            rows = [x for x in rows if x.get("assertion_status") in statuses]
        if roles:
            rows = [x for x in rows if x.get("record_role") in roles]
        if predicate:
            rows = [x for x in rows if (x.get("statement") or {}).get("predicate") == predicate]
        if subject_id:
            rows = [
                x for x in rows
                if self._statement_ref((x.get("statement") or {}).get("subject")) == subject_id
            ]
        if object_id:
            rows = [
                x for x in rows
                if self._statement_ref((x.get("statement") or {}).get("object")) == object_id
            ]

        raw_count = len(rows)
        limit = context.max_items or raw_count
        selected = rows[:limit]
        items = [
            {
                "kind": "assertion",
                "semantic_role": "source_assertion",
                **row,
            }
            for row in selected
        ]
        return AdapterResult(
            items=items,
            metadata={
                "schema_version": "6.0",
                "state_id": state.get("state_id"),
                "source_bytes_preserved": True,
            },
            raw_item_count=raw_count,
            truncated=raw_count > limit,
        )
