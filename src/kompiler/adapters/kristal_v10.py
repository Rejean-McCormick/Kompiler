from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from kompiler.adapters.base import Adapter, AdapterContext, AdapterResult
from kompiler.adapters.common import opcap
from kompiler.errors import AdapterError
from kompiler.kristal_standard import get_standard
from kompiler.protocol.canonical import canonical_bytes
from kompiler.protocol.models import OperationCapability, SourceDescriptor

PUBLICATION_TYPE = "kristal_publication"
MANIFEST_TYPE = "kristal_publication_bundle_manifest"
MANIFEST_PROFILE = "kristal.publication-bundle/1.0"


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise AdapterError("INVALID_SOURCE", f"cannot parse {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise AdapterError("INVALID_SOURCE", f"{path.name} must contain a JSON object")
    return value


def _sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def find_v10_publication(root: str | Path) -> Path | None:
    p = Path(root).expanduser().resolve()
    candidates: list[Path] = []
    if p.is_file() and p.name == "publication.json":
        candidates = [p.parent]
    elif p.is_dir():
        candidates = [p, p / "dist" / "kristal-publication", p / ".kristal" / "publication"]
        candidates += [x.parent for x in p.glob("**/publication.json") if len(x.relative_to(p).parts) <= 5]
    seen: set[Path] = set()
    for bundle in candidates:
        try:
            bundle = bundle.resolve()
        except OSError:
            continue
        if bundle in seen:
            continue
        seen.add(bundle)
        pub = bundle / "publication.json"
        manifest = bundle / "bundle-manifest.json"
        state = bundle / "state-snapshot.json"
        if not (pub.is_file() and manifest.is_file() and state.is_file()):
            continue
        try:
            value = json.loads(pub.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(value, dict) and value.get("schema_version") == "10.0" and value.get("artifact_type") == PUBLICATION_TYPE:
            return bundle
    return None


def target_id_for_v10(bundle: Path) -> str:
    try:
        pub = _json(bundle / "publication.json")
        ident = str(pub.get("publication_id") or "")
    except Exception:
        ident = ""
    return f"KristalV10Publication:{ident or bundle.name}"


def verify_bundle(bundle: Path) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    pub = _json(bundle / "publication.json")
    manifest = _json(bundle / "bundle-manifest.json")
    state = _json(bundle / "state-snapshot.json")

    standard = get_standard()
    pub_schema_path = standard.schema_for_artifact(PUBLICATION_TYPE)
    state_schema_path = standard.schema_for_artifact("kristal_state_snapshot")
    if pub_schema_path is None or state_schema_path is None:
        raise AdapterError("KRISTAL_V10_SCHEMA_MISSING", "Kristal Standard v10/v9 schemas are not available")

    for label, value, schema_path in (
        ("publication.json", pub, pub_schema_path),
        ("state-snapshot.json", state, state_schema_path),
    ):
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        errs = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda e: list(e.absolute_path))
        for err in errs[:32]:
            issues.append({"path": label + ("." + ".".join(map(str, err.absolute_path)) if err.absolute_path else ""), "code": "SCHEMA_VIOLATION", "message": err.message})

    if manifest.get("artifact_type") != MANIFEST_TYPE or manifest.get("profile") != MANIFEST_PROFILE:
        issues.append({"path": "bundle-manifest.json", "code": "UNSUPPORTED_PROFILE", "message": "unsupported publication bundle manifest"})

    payloads = manifest.get("payloads")
    if not isinstance(payloads, list):
        issues.append({"path": "bundle-manifest.json.payloads", "code": "INVALID_TYPE", "message": "payloads must be array"})
        payloads = []

    bundle_root = bundle.resolve()
    for i, resource in enumerate(payloads):
        if not isinstance(resource, dict):
            issues.append({"path": f"bundle-manifest.json.payloads[{i}]", "code": "INVALID_TYPE", "message": "payload must be object"})
            continue
        raw = resource.get("path")
        if not isinstance(raw, str) or not raw or Path(raw).is_absolute() or ".." in Path(raw).parts:
            issues.append({"path": f"bundle-manifest.json.payloads[{i}].path", "code": "INVALID_PATH", "message": "payload path must be relative and contained"})
            continue
        file = (bundle_root / raw).resolve()
        try:
            file.relative_to(bundle_root)
        except ValueError:
            issues.append({"path": f"bundle-manifest.json.payloads[{i}].path", "code": "INVALID_PATH", "message": "payload escapes bundle"})
            continue
        if not file.is_file():
            issues.append({"path": raw, "code": "MISSING_RESOURCE", "message": "payload missing"})
            continue
        data = file.read_bytes()
        if resource.get("size") != len(data):
            issues.append({"path": raw, "code": "SIZE_MISMATCH", "message": f"expected {resource.get('size')}, got {len(data)}"})
        got = _sha256_bytes(data)
        if resource.get("blob_digest") != got:
            issues.append({"path": raw, "code": "DIGEST_MISMATCH", "message": f"expected {resource.get('blob_digest')}, got {got}"})

    manifest_bytes = (bundle / "bundle-manifest.json").read_bytes()
    manifest_digest = _sha256_bytes(manifest_bytes)
    bound_manifest = (((pub.get("extensions") or {}).get("bundle") or {}).get("manifest_blob_digest"))
    if bound_manifest != manifest_digest:
        issues.append({"path": "publication.json.extensions.bundle.manifest_blob_digest", "code": "DIGEST_MISMATCH", "message": "publication does not bind exact bundle manifest bytes"})

    projection = {
        "node_id": pub.get("node_id"),
        "binding_id": pub.get("binding_id"),
        "state": pub.get("state"),
        "bundle_manifest_digest": manifest_digest,
    }
    expected_id = "urn:kristal:publication:sha256:" + hashlib.sha256(canonical_bytes(projection)).hexdigest()
    if pub.get("publication_id") != expected_id:
        issues.append({"path": "publication.json.publication_id", "code": "DIGEST_MISMATCH", "message": "publication_id does not match publication identity projection"})

    for i, resource in enumerate(pub.get("resources") or []):
        if not isinstance(resource, dict):
            continue
        locator = resource.get("locator")
        if not isinstance(locator, str) or not locator.startswith("bundle://"):
            continue
        rel = locator[len("bundle://"):]
        if not rel or Path(rel).is_absolute() or ".." in Path(rel).parts:
            issues.append({"path": f"publication.json.resources[{i}].locator", "code": "INVALID_PATH", "message": "bundle locator invalid"})
            continue
        file = (bundle_root / rel).resolve()
        if not file.is_file():
            issues.append({"path": rel, "code": "MISSING_RESOURCE", "message": "publication resource missing"})
            continue
        data = file.read_bytes()
        if resource.get("size") != len(data):
            issues.append({"path": rel, "code": "SIZE_MISMATCH", "message": f"expected {resource.get('size')}, got {len(data)}"})
        got = _sha256_bytes(data)
        if resource.get("blob_digest") != got:
            issues.append({"path": rel, "code": "DIGEST_MISMATCH", "message": f"expected {resource.get('blob_digest')}, got {got}"})

    pub_state = pub.get("state") if isinstance(pub.get("state"), dict) else {}
    if pub_state.get("state_ref") != state.get("state_ref") or pub_state.get("logical_commitment") != state.get("logical_commitment"):
        issues.append({"path": "publication.json.state", "code": "STATE_BINDING_MISMATCH", "message": "publication state does not match bundled state snapshot"})

    return {
        "ok": not issues,
        "issues": issues,
        "publication_id": pub.get("publication_id"),
        "state": pub.get("state"),
        "bundle_manifest_digest": manifest_digest,
    }


class KristalV10PublicationAdapter(Adapter):
    adapter_id = "kristal-v10-publication"
    adapter_version = "1.0.0"
    kind = "kristal"

    def __init__(self, root: str | Path, target_id: str | None = None):
        bundle = find_v10_publication(root)
        if bundle is None:
            raise AdapterError("SOURCE_NOT_FOUND", f"no Kristal v10 publication bundle found at {root}")
        self.bundle = bundle
        self.root = bundle
        self.publication = _json(bundle / "publication.json")
        self.state = _json(bundle / "state-snapshot.json")
        self.verification = verify_bundle(bundle)
        if not self.verification["ok"]:
            raise AdapterError("INVALID_V10_PUBLICATION", "Kristal v10 publication bundle failed verification", {"issues": self.verification["issues"]})
        self.target_id = target_id or target_id_for_v10(bundle)

    def source_descriptor(self):
        state = self.publication.get("state") or {}
        commitment = state.get("logical_commitment") or {}
        return SourceDescriptor(
            kristal_schema_version="10.0",
            state_id=state.get("state_ref"),
            snapshot_id=commitment.get("digest"),
            contract_family="kristal.publication",
            root_hint=self.bundle.name,
            integrity="verified-v10-publication-bundle",
            publication_id=self.publication.get("publication_id"),
            node_id=self.publication.get("node_id"),
            binding_id=self.publication.get("binding_id"),
        )

    def health(self):
        return {
            "ok": True,
            "adapter_id": self.adapter_id,
            "target_id": self.target_id,
            "publication_id": self.publication.get("publication_id"),
            "state": self.publication.get("state"),
            "bundle_manifest_digest": self.verification.get("bundle_manifest_digest"),
        }

    def capabilities(self) -> list[OperationCapability]:
        return [
            opcap("publication", "Read the verified v10 Publication Record and bundle binding.", {}, max_items=1, record_kinds=["kristal_publication"]),
            opcap("state", "Read the v9 State Snapshot bound by the verified v10 Publication Record.", {}, max_items=1, record_kinds=["kristal_state_snapshot"]),
        ]

    async def execute(self, operation: str, params: dict[str, Any], context: AdapterContext) -> AdapterResult:
        if operation == "publication":
            return AdapterResult(items=[{"kind": "kristal_publication", **self.publication}], metadata={"bundle_verified": True}, raw_item_count=1)
        if operation == "state":
            return AdapterResult(items=[{"kind": "kristal_state_snapshot", **self.state}], metadata={"publication_id": self.publication.get("publication_id"), "bundle_verified": True}, raw_item_count=1)
        raise AdapterError("UNKNOWN_OPERATION", f"{self.target_id} does not expose operation {operation}")
