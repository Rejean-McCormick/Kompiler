from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kompiler.errors import StandardError

_LOCK_PATH = Path(__file__).with_name("kristal-standard.lock.json")
_configured_root: Path | None = None
_configured_contract_sha256: str | None = None


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise StandardError("KRISTAL_STANDARD_INVALID", f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise StandardError("KRISTAL_STANDARD_INVALID", f"expected JSON object in {path}")
    return value


def standard_lock() -> dict[str, Any]:
    return _load_json(_LOCK_PATH)


def configure_standard_root(root: str | Path | None, contract_set_sha256: str | None = None) -> None:
    global _configured_root, _configured_contract_sha256
    _configured_root = Path(root).expanduser().resolve() if root else None
    _configured_contract_sha256 = contract_set_sha256


def resolve_standard_root(root: str | Path | None = None) -> Path:
    raw = root or _configured_root or os.getenv("KOMPILER_KRISTAL_STANDARD_ROOT")
    if not raw:
        raise StandardError(
            "KRISTAL_STANDARD_UNAVAILABLE",
            "Kristal Standard root is not configured",
            {"env": "KOMPILER_KRISTAL_STANDARD_ROOT", "expected_version": standard_lock()["version"]},
        )
    path = Path(raw).expanduser().resolve()
    if not path.is_dir():
        raise StandardError("KRISTAL_STANDARD_UNAVAILABLE", f"Kristal Standard root does not exist: {path}")
    return path


@dataclass(slots=True)
class KristalStandard:
    root: Path
    release: dict[str, Any]
    contract_set: dict[str, Any]
    lock: dict[str, Any]
    _artifact_schemas: dict[str, Path] = field(default_factory=dict)

    @classmethod
    def load(cls, root: str | Path | None = None) -> "KristalStandard":
        base = resolve_standard_root(root)
        lock = standard_lock()
        release_path = base / "contracts" / "release.json"
        contract_path = base / lock["contract_set"]
        if not release_path.is_file() or not contract_path.is_file():
            raise StandardError(
                "KRISTAL_STANDARD_INVALID",
                "configured Kristal root is missing release/contract metadata",
                {"root": str(base)},
            )
        release = _load_json(release_path)
        contract_set = _load_json(contract_path)
        actual_version = str(release.get("version") or "")
        if actual_version == lock["version"]:
            expected_hash = lock.get("contract_set_sha256")
        elif actual_version in lock.get("additional_supported_versions", []):
            explicit_pin = _configured_contract_sha256 or os.getenv("KOMPILER_KRISTAL_CONTRACT_SET_SHA256")
            expected_hash = explicit_pin or lock.get("additional_contract_set_pins", {}).get(actual_version)
            if not isinstance(expected_hash, str) or len(expected_hash) != 64 or any(c not in "0123456789abcdefABCDEF" for c in expected_hash):
                raise StandardError(
                    "KRISTAL_STANDARD_PIN_REQUIRED",
                    f"Kristal {actual_version} requires an exact contract-set SHA-256 pin",
                    {"version": actual_version, "env": "KOMPILER_KRISTAL_CONTRACT_SET_SHA256"},
                )
            expected_hash = expected_hash.lower()
        else:
            raise StandardError(
                "KRISTAL_STANDARD_MISMATCH",
                f"Unsupported Kristal Framework version: {actual_version or 'unknown'}",
                {"supported": [lock["version"], *lock.get("additional_supported_versions", [])]},
            )
        actual_hash = hashlib.sha256(contract_path.read_bytes()).hexdigest()
        if isinstance(expected_hash, str) and len(expected_hash) == 64 and actual_hash != expected_hash:
            raise StandardError(
                "KRISTAL_STANDARD_MISMATCH",
                "Kristal contract-set hash does not match Kompiler lock",
                {"expected": expected_hash, "actual": actual_hash},
            )
        if expected_hash is None and lock.get("lock_strength") != "draft-version-pin":
            raise StandardError("KRISTAL_STANDARD_INVALID", "unpinned contract set requires explicit draft-version-pin mode")
        obj = cls(root=base, release=release, contract_set=contract_set, lock=lock)
        obj._index_artifact_schemas()
        return obj

    @property
    def version(self) -> str:
        return str(self.release["version"])

    @property
    def v7_schema_root(self) -> Path:
        semantic = self.release.get("semantic_baseline") or {}
        return self.root / str(semantic.get("schema_root") or self.release.get("v7_schema_root", "schemas/v7"))

    @property
    def v8_schema_root(self) -> Path:
        query = self.release.get("query_baseline") or {}
        return self.root / str(query.get("schema_root") or "schemas/v8")

    @property
    def v9_schema_root(self) -> Path:
        v9 = self.release.get("v9") or {}
        return self.root / str(v9.get("schema_root") or "schemas/v9")

    @property
    def v10_schema_root(self) -> Path:
        v10 = self.release.get("v10") or {}
        return self.root / str(v10.get("schema_root") or "schemas/v10")

    @property
    def tck_root(self) -> Path:
        return self.root / str(self.release.get("v7_tck_root", "tck/v7/vectors"))

    def _index_artifact_schemas(self) -> None:
        self._artifact_schemas.clear()
        for schema_root in (self.v7_schema_root, self.v8_schema_root, self.v9_schema_root, self.v10_schema_root):
            if not schema_root.is_dir():
                raise StandardError("KRISTAL_STANDARD_INVALID", f"missing schema root: {schema_root}")
            for path in sorted(schema_root.glob("*.schema.json")):
                schema = _load_json(path)
                props = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
                artifact = props.get("artifact_type") if isinstance(props, dict) else None
                const = artifact.get("const") if isinstance(artifact, dict) else None
                if isinstance(const, str):
                    self._artifact_schemas[const] = path
        # GitHub host binding lives under the v10 reference host profile.
        github_root = self.root / "profiles" / "github" / "schemas"
        if github_root.is_dir():
            for path in sorted(github_root.glob("*.schema.json")):
                schema = _load_json(path)
                props = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
                artifact = props.get("artifact_type") if isinstance(props, dict) else None
                const = artifact.get("const") if isinstance(artifact, dict) else None
                if isinstance(const, str):
                    self._artifact_schemas[const] = path

    def schema_for_artifact(self, artifact_type: str) -> Path | None:
        return self._artifact_schemas.get(artifact_type)

    @property
    def portable_state_schema(self) -> Path:
        portable = self.release.get("portable_contract") or {}
        rel = portable.get("schema") or "schemas/v6/kristal-state.schema.json"
        path = (self.root / str(rel)).resolve()
        if not path.is_file():
            raise StandardError("KRISTAL_STANDARD_INVALID", f"missing portable state schema: {path}")
        return path

    @property
    def v7_extension_schema(self) -> Path:
        path = self.v7_schema_root / "kristal-v7-extension.schema.json"
        if not path.is_file():
            raise StandardError("KRISTAL_STANDARD_INVALID", f"missing v7 extension schema: {path}")
        return path

    def describe(self) -> dict[str, Any]:
        return {
            "root": str(self.root),
            "version": self.version,
            "contract_set_sha256": hashlib.sha256((self.root / self.lock["contract_set"]).read_bytes()).hexdigest(),
            "lock_strength": self.lock.get("lock_strength"),
            "v9_schema_root": str(self.v9_schema_root),
            "v10_schema_root": str(self.v10_schema_root),
            "framework_commit": self.lock.get("framework_commit") if self.version == self.lock["version"] else None,
            "artifact_schema_count": len(self._artifact_schemas),
            "portable_state_schema": str(self.portable_state_schema),
        }


def get_standard(root: str | Path | None = None) -> KristalStandard:
    return KristalStandard.load(root)
