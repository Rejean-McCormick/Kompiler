from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from kompiler.errors import AdapterError
from kompiler.protocol.canonical import prefixed_hash
from kompiler.protocol.models import SourceDescriptor
from kompiler.kristal_standard import get_standard


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise AdapterError("INVALID_SOURCE", f"cannot parse JSON artifact {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AdapterError("INVALID_SOURCE", f"expected JSON object in {path}")
    return value


def _validator_for(artifact_type: str) -> Draft202012Validator | None:
    schema_path = get_standard().schema_for_artifact(artifact_type)
    if schema_path is None:
        return None
    return Draft202012Validator(_read_json(schema_path))


def validate_v7_artifact(value: dict[str, Any], *, path: Path | None = None) -> None:
    artifact_type = value.get("artifact_type")
    if not isinstance(artifact_type, str):
        raise AdapterError("INVALID_V7_ARTIFACT", "v7 artifact is missing artifact_type")
    validator = _validator_for(artifact_type)
    if validator is None:
        raise AdapterError("UNKNOWN_V7_ARTIFACT", f"unsupported v7 artifact_type {artifact_type!r}")
    errors = sorted(validator.iter_errors(value), key=lambda e: list(e.absolute_path))
    if errors:
        where = f" in {path}" if path else ""
        raise AdapterError(
            "INVALID_V7_ARTIFACT",
            f"v7 artifact failed schema validation{where}",
            {
                "artifact_type": artifact_type,
                "errors": [
                    {"path": list(e.absolute_path), "message": e.message}
                    for e in errors[:32]
                ],
            },
        )


def find_kristall_manifest(root: str | Path) -> Path | None:
    p = Path(root).expanduser().resolve()
    if p.is_file():
        try:
            value = _read_json(p)
        except AdapterError:
            return None
        return p if value.get("artifact_type") == "kristall_manifest" else None
    if not p.is_dir():
        return None
    candidates: list[Path] = []
    for name in ("kristall-manifest.json", "kristall_manifest.json", "manifest.json"):
        candidates.append(p / name)
    candidates.extend(sorted(p.glob("*manifest*.json")))
    candidates.extend(sorted(p.glob("*/*manifest*.json")))
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen or not candidate.is_file():
            continue
        seen.add(candidate)
        try:
            value = _read_json(candidate)
        except AdapterError:
            continue
        if value.get("artifact_type") == "kristall_manifest" and value.get("schema_version") == "7.0":
            return candidate.resolve()
    return None


@dataclass(slots=True)
class KristallDeployment:
    manifest_path: Path
    manifest: dict[str, Any]
    registries: dict[str, dict[str, Any]]
    registry_paths: dict[str, Path]

    @classmethod
    def load(cls, root: str | Path) -> "KristallDeployment":
        manifest_path = find_kristall_manifest(root)
        if manifest_path is None:
            raise AdapterError("SOURCE_NOT_FOUND", f"no Kristall v7 manifest found below {root}")
        manifest = _read_json(manifest_path)
        validate_v7_artifact(manifest, path=manifest_path)
        registries: dict[str, dict[str, Any]] = {}
        registry_paths: dict[str, Path] = {}
        for name, ref in (manifest.get("registries") or {}).items():
            if not isinstance(ref, str) or not ref:
                continue
            path = (manifest_path.parent / ref).resolve()
            if manifest_path.parent not in path.parents and path != manifest_path.parent:
                raise AdapterError("PATH_OUTSIDE_ALLOWED_ROOT", f"registry {name} escaped Kristall root")
            if not path.exists():
                # Registries MAY be sharded/external. Missing local files remain visible in health,
                # but loading a surface that needs them will fail explicitly.
                continue
            value = _read_json(path)
            validate_v7_artifact(value, path=path)
            registries[name] = value
            registry_paths[name] = path
        return cls(manifest_path=manifest_path, manifest=manifest, registries=registries, registry_paths=registry_paths)

    @property
    def root(self) -> Path:
        return self.manifest_path.parent

    @property
    def kristall_id(self) -> str:
        return str(self.manifest["kristall_id"])

    @property
    def namespace_id(self) -> str:
        return str(self.manifest["namespace_id"])

    @property
    def snapshot_id(self) -> str:
        registry_hashes = {
            name: prefixed_hash("v7meta", value)
            for name, value in sorted(self.registries.items())
        }
        body = {
            "canonicalization_profile": self.manifest.get("canonicalization_profile", "kristal.v7:jcs-rfc8785"),
            "manifest": self.manifest,
            "registries": registry_hashes,
        }
        return prefixed_hash("kristall", body)

    def source_descriptor(self) -> SourceDescriptor:
        return SourceDescriptor(
            kristal_schema_version="7.0",
            state_id=self.snapshot_id,
            snapshot_id=self.snapshot_id,
            contract_family="kristall",
            kristall_id=self.kristall_id,
            namespace_id=self.namespace_id,
            canonicalization_profile=str(
                self.manifest.get("canonicalization_profile", "kristal.v7:jcs-rfc8785")
            ),
            root_hint=self.root.name,
            integrity="kristal.v7:jcs-rfc8785",
            standard_version=get_standard().version,
        )

    def registry(self, name: str, *, required: bool = False) -> dict[str, Any]:
        value = self.registries.get(name)
        if value is None and required:
            ref = (self.manifest.get("registries") or {}).get(name)
            raise AdapterError(
                "SOURCE_NOT_FOUND",
                f"Kristall registry {name!r} is not locally available",
                {"registry": name, "reference": ref},
            )
        return value or {}

    def subjects(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for source in (self.registry("toc").get("subjects", []), self.manifest.get("subjects", [])):
            for item in source if isinstance(source, list) else []:
                if not isinstance(item, dict):
                    continue
                sid = str(item.get("subject_id") or "")
                if sid and sid not in seen:
                    seen.add(sid)
                    rows.append(item)
        return rows

    def health(self) -> dict[str, Any]:
        declared = self.manifest.get("registries") or {}
        missing = sorted(name for name, ref in declared.items() if isinstance(ref, str) and name not in self.registries)
        return {
            "ok": not missing,
            "manifest": str(self.manifest_path),
            "kristall_id": self.kristall_id,
            "namespace_id": self.namespace_id,
            "snapshot_id": self.snapshot_id,
            "standard_version": get_standard().version,
            "loaded_registries": sorted(self.registries),
            "missing_local_registries": missing,
        }
