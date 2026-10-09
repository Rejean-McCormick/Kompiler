import json
import os
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from kompiler.adapters.kristall import KristallAdapter
from kompiler.adapters.kristal_v6 import KristalV6StateAdapter
from kompiler.api.app import create_app
from kompiler.config import AppConfig, StorageConfig
from kompiler.errors import AdmissionError
from kompiler.kristal_standard import get_standard
from kompiler.kristall import materialize_v6_projection
from kompiler.planner import build_plan
from kompiler.protocol.models import QueryPlan
from kompiler.registry import AdapterRegistry, discover
from kompiler.runtime import KompilerRuntime
from kompiler.storage import SQLiteStore

pytestmark = pytest.mark.skipif(
    not os.getenv("KOMPILER_KRISTAL_STANDARD_ROOT"),
    reason="cross-repo Kristal integration requires KOMPILER_KRISTAL_STANDARD_ROOT",
)


def _standard():
    return get_standard()


def _deployment(tmp_path: Path) -> Path:
    """Build a Kompiler-specific integration deployment from the external Standard TCK.

    Nothing is vendored in the repository: official vectors are copied only into pytest's
    temporary directory, then a couple of Mesh edges are added to exercise Surface logic.
    """
    src = _standard().tck_root
    dst = tmp_path / "kristall"
    dst.mkdir()
    for path in src.glob("*.json"):
        shutil.copy2(path, dst / path.name)

    manifest_path = dst / "kristall-manifest.example.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["sources"] = [
        {"source_id": "source:formal", "state_id": "sha256:source-formal", "status": "active"},
        {"source_id": "source:informal", "state_id": "sha256:source-informal", "status": "active"},
    ]
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    mesh_path = dst / manifest["registries"]["mesh"]
    mesh = json.loads(mesh_path.read_text())
    mesh["edges"].extend(
        [
            {
                "edge_id": "edge:kompiler-axis",
                "from": {"kind": "axis", "id": "KQ2001"},
                "relation": "KP1001",
                "to": {"kind": "entity", "id": "KQ1001"},
                "edge_semantics": "orientation_affinity",
                "status": "accepted",
                "resonance_refs": [],
            },
            {
                "edge_id": "edge:kompiler-subject",
                "from": {"kind": "subject", "id": "subject:power"},
                "relation": "KP1001",
                "to": {"kind": "entity", "id": "KQ1001"},
                "edge_semantics": "membership",
                "status": "accepted",
                "resonance_refs": [],
            },
        ]
    )
    mesh_path.write_text(json.dumps(mesh, indent=2) + "\n")
    return dst


def _runtime(tmp_path: Path):
    adapter = KristallAdapter(_deployment(tmp_path))
    reg = AdapterRegistry()
    reg.register(adapter)
    cfg = AppConfig(storage=StorageConfig(database=tmp_path / "k.db", cache=True))
    return adapter, KompilerRuntime(cfg, reg, SQLiteStore(cfg.storage.database))


def _query(target: str) -> QueryPlan:
    return QueryPlan.model_validate(
        {
            "version": "1.1",
            "request_id": "v7-test",
            "topic": "power",
            "operations": [
                {
                    "id": "surface",
                    "target": target,
                    "operation": "surface",
                    "surface": {
                        "subject": {"subject_id": "subject:power"},
                        "orientation": {"primary_axis": "KQ2001"},
                    },
                }
            ],
        }
    )


def test_external_standard_contract_is_pinned():
    standard = _standard()
    assert standard.version in {standard.lock["version"], *standard.lock["additional_supported_versions"]}
    assert standard.lock["integration"] == "external-readonly"
    assert standard.portable_state_schema.name == "kristal-state.schema.json"
    assert standard.schema_for_artifact("kristall_toc_registry") is not None


def test_official_v7_vectors_validate_against_external_standard():
    standard = _standard()
    pairs = {
        "kristall-manifest.example.json": "kristall_manifest",
        "entity-registry.example.json": "kristall_entity_registry",
        "axis-registry.example.json": "kristall_axis_registry",
        "axis-type-registry.example.json": "kristall_axis_type_registry",
        "kos-registry.example.json": "kristall_kos_registry",
        "toc-registry-100-seed.example.json": "kristall_toc_registry",
        "mesh.example.json": "kristall_mesh",
        "projection-recipe.example.json": "kristall_projection_recipe",
        "crystallization-record.example.json": "kristall_crystallization_record",
        "assertion-family-registry.example.json": "kristall_assertion_family_registry",
        "property-registry.example.json": "kristall_property_registry",
        "assertion-registry.example.json": "kristall_assertion_registry",
        "source-registry.example.json": "kristall_source_registry",
        "resonance.example.json": "semantic_resonance_set",
    }
    for example, artifact_type in pairs.items():
        schema_path = standard.schema_for_artifact(artifact_type)
        assert schema_path is not None
        Draft202012Validator(json.loads(schema_path.read_text())).validate(
            json.loads((standard.tck_root / example).read_text())
        )


def test_discovery_finds_kristall(tmp_path):
    deployment = _deployment(tmp_path)
    hits = discover([deployment])
    assert any(x["adapter_type"] == "kristall-v7" for x in hits)
    assert any(x["target_id"] == "Kristall:kristall-main" for x in hits)


def test_surface_is_required_for_native_surface(tmp_path):
    adapter, rt = _runtime(tmp_path)
    q = QueryPlan.model_validate(
        {"request_id": "x", "operations": [{"id": "s", "target": adapter.target_id, "operation": "surface"}]}
    )
    with pytest.raises(AdmissionError) as exc:
        build_plan(q, rt.registry, config=rt.config)
    assert exc.value.code == "SURFACE_REQUIRED"
    rt.close()


@pytest.mark.asyncio
async def test_v7_surface_roundtrip_and_projection(tmp_path):
    adapter, rt = _runtime(tmp_path)
    pack = await rt.run(_query(adapter.target_id))
    assert pack.version == "1.1"
    assert pack.summary.surface_count == 1
    assert pack.summary.axis_count == 1
    assert pack.summary.resonance_count == 1
    assert pack.surfaces[0].orientation.primary_axis == "KQ2001"
    assert pack.surfaces[0].selection["resonance_semantics"] == "candidate_signal_only"
    assert all(r.kind != "semantic_resonance" for r in pack.records)
    projection = materialize_v6_projection(pack)
    assert projection["schema_version"] == "6.0"
    assert projection["artifact_type"] == "kristal_state"
    ext = projection["extensions"]["kristal_v7"]
    assert ext["orientation"]["primary_axis"] == "KQ2001"
    assert ext["generated_from"]["source_state_refs"] == ["sha256:source-formal", "sha256:source-informal"]
    Draft202012Validator(json.loads(_standard().portable_state_schema.read_text())).validate(projection)
    rt.close()


@pytest.mark.asyncio
async def test_draft32_toc_kos_and_axis_type_operations(tmp_path):
    adapter, rt = _runtime(tmp_path)
    query = QueryPlan.model_validate(
        {
            "version": "1.1",
            "request_id": "v7-draft32",
            "operations": [
                {"id": "types", "target": adapter.target_id, "operation": "axis-types", "params": {}},
                {"id": "kos", "target": adapter.target_id, "operation": "kos", "params": {}},
                {"id": "toc", "target": adapter.target_id, "operation": "toc", "params": {"kind": "subjects"}},
            ],
        }
    )
    pack = await rt.run(query)
    kinds = {r.kind for r in pack.records}
    assert "axis_type" in kinds
    assert "kos_system" in kinds
    assert "toc_subject" in kinds
    rt.close()


@pytest.mark.asyncio
async def test_v7_semantic_hash_is_stable_across_runs(tmp_path):
    adapter, rt = _runtime(tmp_path)
    p1 = await rt.run(_query(adapter.target_id))
    p2 = await rt.run(_query(adapter.target_id))
    assert p1.context_pack_id == p2.context_pack_id
    assert p2.execution.cache_hits == 1
    rt.close()


def test_v7_projection_api_roundtrip(tmp_path):
    adapter, rt = _runtime(tmp_path)
    with TestClient(create_app(rt)) as client:
        run = client.post("/v1/runs", json=_query(adapter.target_id).model_dump(mode="json", exclude_none=True))
        assert run.status_code == 200
        projection = client.post("/v1/projections/v6", json={"context_pack": run.json()})
        assert projection.status_code == 200
        artifact = projection.json()
        assert artifact["schema_version"] == "6.0"
        assert artifact["artifact_type"] == "kristal_state"
    rt.close()


def test_capabilities_advertise_current_v7_projection_profile(tmp_path):
    adapter, rt = _runtime(tmp_path)
    snapshot = rt.capabilities()
    assert snapshot.runtime.standard_support["kristall"] == ["7.0", "8.0"]
    assert snapshot.runtime.standard_support["kristal_hosting"] == ["10.0"]
    assert snapshot.runtime.conformance_profiles["kristal_v10"] == "V10-Publication-Reader"
    assert snapshot.runtime.conformance_profiles["kristal_v7"] == "V7-Projection"
    assert adapter.source_descriptor().standard_version == _standard().version
    rt.close()


@pytest.mark.asyncio
async def test_generic_v6_reader_accepts_portable_state_unchanged(tmp_path):
    source_path = _standard().tck_root / "v6-compatible-projection.example.json"
    before = source_path.read_bytes()
    adapter = KristalV6StateAdapter(source_path)
    reg = AdapterRegistry()
    reg.register(adapter)
    cfg = AppConfig(storage=StorageConfig(database=tmp_path / "v6.db", cache=True))
    rt = KompilerRuntime(cfg, reg, SQLiteStore(cfg.storage.database))
    query = QueryPlan.model_validate(
        {
            "version": "1.1",
            "request_id": "v6-reader",
            "operations": [{"id": "source", "target": adapter.target_id, "operation": "assertions", "params": {}}],
        }
    )
    pack = await rt.run(query)
    source_doc = json.loads(source_path.read_text())
    assert pack.summary.record_count == len(source_doc.get("assertions", []))
    assert all(r.semantic_role == "source_assertion" for r in pack.records)
    assert adapter.source_descriptor().contract_family == "kristal_state"
    assert source_path.read_bytes() == before
    rt.close()


def test_generic_v6_reader_discovery(tmp_path):
    src = _standard().tck_root / "v6-compatible-projection.example.json"
    state = tmp_path / "portable.json"
    state.write_bytes(src.read_bytes())
    hits = discover([tmp_path])
    assert any(x["adapter_type"] == "kristal-v6-state" for x in hits)
    hit = next(x for x in hits if x["adapter_type"] == "kristal-v6-state")
    assert hit["root"] == str(state.resolve())
    assert hit["target_id"].startswith("KristalState:")
