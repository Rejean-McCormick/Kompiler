"""Local v11 reader: fixture guards + optional real Framework/Pack qualification."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import pytest

from kompiler.adapters.base import AdapterContext
from kompiler.adapters.kristal_v11 import KristalV11ReadViewAdapter, _pinned_pack, _view_guard
from kompiler.adapters.manifest import AdapterManifest
from kompiler.errors import AdapterError
from kompiler.normalization.normalizer import normalize_result
from kompiler.registry import AdapterRegistry, discover


def view():
    return {
        "profile": "kristal.integration.read-view/v11.0-draft.1", "derived_only": True,
        "source": {"namespace_id": "example.org/demo", "framework_version": "11.0.0-draft.4", "graph_id": "test",
                   **{x + "_sha256": "a" * 64 for x in ("graph", "registry", "crosswalk", "catalog")}},
        "requested_locale": "fr-CA", "coverage_counts": {"direct": 0, "fallback": 1, "missing": 1},
        "presentation": [
            {"kind": "entity", "semantic_id": "KQ1", "lexical": {"status": "fallback", "effective_locale": "fr", "layer_id": "reviewed", "term": "un terme"}},
            {"kind": "property", "semantic_id": "KP1", "lexical": {"status": "missing"}},
        ],
        "assertions": [{"id": "KA1", "subject": "KQ1", "predicate": "KP1", "object": {"kind": "literal", "datatype": "string", "value": "text"}, "sources": ["KS1"]}],
    }


def validated(monkeypatch, tmp_path, value):
    paths = {}
    for x in ("graph", "registry", "crosswalk", "catalog"):
        p = tmp_path / (x + ".json")
        p.write_text("{}")
        paths[x] = p
        from kompiler.adapters import kristal_v11
        value["source"][x + "_sha256"] = kristal_v11._sha(p)
    return _view_guard(value, locale="fr-CA", namespace="example.org/demo", paths=paths)


def test_fixture_guard_valid(tmp_path, monkeypatch):
    assert validated(monkeypatch, tmp_path, view())["derived_only"] is True


@pytest.mark.parametrize("mutation", [
    lambda x: x.update(derived_only=False),
    lambda x: x["source"].update(framework_version="11.0.0-draft.0"),
    lambda x: x["coverage_counts"].update(fallback=2),
    lambda x: x["presentation"][0]["lexical"].update(status="direct"),
    lambda x: x["presentation"][1]["lexical"].update(term="invented"),
    lambda x: x["presentation"][0].update(semantic_id="Q1"),
    lambda x: x["assertions"][0].update(subject="KQ999"),
    lambda x: x["assertions"][0].update(subject="KP1"),
    lambda x: x["assertions"][0].update(qualifiers=[{"predicate":"KP1", "object":{"kind":"entity", "id":"KQ999"}}]),
    lambda x: x["assertions"][0].update(sources=["WikidataQ1"]),
    lambda x: x["assertions"][0].update(object={"kind": "literal", "value": "text"}),
    lambda x: x.update(requested_locale="en"),
])
def test_fixture_guard_fail_closed(tmp_path, monkeypatch, mutation):
    value = view()
    mutation(value)
    with pytest.raises(AdapterError):
        validated(monkeypatch, tmp_path, value)



def test_guard_rejects_source_digest_drift(tmp_path, monkeypatch):
    value = view()
    validated(monkeypatch, tmp_path, value)
    value["source"]["graph_sha256"] = "b" * 64
    paths = {x: tmp_path / (x + ".json") for x in ("graph", "registry", "crosswalk", "catalog")}
    with pytest.raises(AdapterError, match="digest"):
        _view_guard(value, locale="fr-CA", namespace="example.org/demo", paths=paths)

def test_no_auto_discovery_for_canonical_v11(tmp_path):
    for name in ("graph.json", "registry.json", "crosswalk.json", "catalog.json"):
        (tmp_path / name).write_text("{}")
    assert all(x["adapter_type"] != "kristal-v11-read-view" for x in discover([tmp_path]))


def test_local_approval_and_pin_required(tmp_path):
    files = {}
    for name in ("graph", "registry", "crosswalk", "catalog"):
        (tmp_path / (name + ".json")).write_text("{}")
        files[name] = name + ".json"
    m = AdapterManifest(id="demo", version="1", target_id="V11", kind="kristal", root=tmp_path,
        adapter_type="kristal-v11-read-view", options={**files})
    with pytest.raises(AdapterError, match="V11_APPROVAL_REQUIRED"):
        KristalV11ReadViewAdapter(m)
    m.options["local_read_approved"] = True
    with pytest.raises(AdapterError, match="INVALID_V11_CONFIG"):
        KristalV11ReadViewAdapter(m)


FRAMEWORK = os.getenv("KOMPILER_V11_FRAMEWORK_ROOT")
PACK = os.getenv("KOMPILER_V11_PACK_ROOT")


def real_adapter():
    root = Path(FRAMEWORK).resolve() / "examples" / "v11"
    manifest = AdapterManifest(id="v11", version="0.1.0", target_id="KristalV11:demo", kind="kristal", root=root,
        adapter_type="kristal-v11-read-view", options={
            "local_read_approved": True, "framework_root": FRAMEWORK, "integration_pack_root": PACK,
            "registry": "identity-registry.example.json", "graph": "semantic-graph.example.json",
            "crosswalk": "external-crosswalk.example.json", "catalog": "dictionaries/catalog.json"})
    return KristalV11ReadViewAdapter(manifest)


@pytest.mark.skipif(not (FRAMEWORK and PACK), reason="requires exact reviewed Framework/Pack checkouts")
def test_real_view_and_normalizer():
    a = real_adapter()
    r = asyncio.run(a.execute("read", {"locale": "fr-CA", "semantic_ids": ["KQ1001", "KQ1002", "KP2001", "KA3001", "KS4001"]},
        AdapterContext(operation_id="read", timeout_ms=30000)))
    assert len(r.items) == 5
    assert r.metadata["coverage_counts"] == {"direct": 0, "fallback": 1, "missing": 2}
    lexical = next(x for x in r.items if x["semantic_id"] == "KQ1001")
    assert lexical["lexical"]["status"] == "fallback"
    assert lexical["lexical"]["effective_locale"] == "fr"
    assert lexical["accepted_external_exact"] == {"system": "wikidata", "id": "Q8018"}
    assert all("term" not in x["lexical"] for x in r.items if x.get("lexical", {}).get("status") == "missing")
    assertion = next(x for x in r.items if x["semantic_id"] == "KA3001")
    assert assertion["subject_ref"] == "KQ1001" and assertion["object_ref"] == "KQ1002"
    assert assertion["canonical_sources"] == ["KS4001"]
    assert r.metadata["publication_authorized"] is False
    normalized = normalize_result(a.target_id, "read", r, a.source_descriptor())
    assert len(normalized.records) == 5
    assert len(normalized.relations) == 1
    assert any(x.referent_id == "KQ1001" for x in normalized.referents)
    assert any(x.source_id.endswith(":KS4001") for x in normalized.sources)
    registry = AdapterRegistry()
    registry.register(a)
    snap = registry.snapshot()
    assert snap.targets[0].adapter.id == "kristal-v11-read-view"
    assert not snap.targets[0].operations[0].semantics.network
    assert not snap.targets[0].operations[0].semantics.supports_reader_policy


@pytest.mark.skipif(not (FRAMEWORK and PACK), reason="requires exact reviewed Framework/Pack checkouts")
def test_real_rejects_unknown_and_selection_limits():
    a = real_adapter()
    ctx = AdapterContext(operation_id="read", timeout_ms=30000, max_items=1)
    with pytest.raises(AdapterError, match="INVALID_PARAMETERS"):
        asyncio.run(a.execute("read", {"locale": "x y", "semantic_ids": ["KQ1001"]}, ctx))
    with pytest.raises(AdapterError, match="UNKNOWN_V11_ID"):
        asyncio.run(a.execute("read", {"locale": "fr-CA", "semantic_ids": ["KQ9999"]}, ctx))
    with pytest.raises(AdapterError, match="RESOURCE_LIMIT_EXCEEDED"):
        asyncio.run(a.execute("read", {"locale": "fr-CA", "semantic_ids": ["KQ1001", "KQ1002"]}, ctx))


@pytest.mark.skipif(not (FRAMEWORK and PACK), reason="requires exact reviewed Framework/Pack checkouts")
def test_real_pack_script_drift_refused(tmp_path):
    import shutil
    a = real_adapter()
    dst = tmp_path / "pack"
    (dst / "tools").mkdir(parents=True)
    (dst / "contracts").mkdir()
    shutil.copy2(a.script, dst / "tools/v11_integration.py")
    shutil.copy2(a.pack / "contracts/v11-framework-pin.json", dst / "contracts/v11-framework-pin.json")
    with (dst / "tools/v11_integration.py").open("a") as f:
        f.write("\n# unapproved mutation\n")
    with pytest.raises(AdapterError, match="UNTRUSTED_V11_PACK"):
        _pinned_pack(dst)


@pytest.mark.skipif(not (FRAMEWORK and PACK), reason="requires exact reviewed Framework/Pack checkouts")
def test_real_tampered_canonical_graph_fails_without_source_mutation(tmp_path):
    import shutil
    a = real_adapter()
    root = tmp_path / "sources"
    shutil.copytree(a.root, root)
    m = AdapterManifest(id="v11", version="1", target_id="Test", kind="kristal", root=root,
        adapter_type="kristal-v11-read-view", options={
        "local_read_approved": True, "framework_root": FRAMEWORK, "integration_pack_root": PACK,
        "registry": "identity-registry.example.json", "graph": "semantic-graph.example.json",
        "crosswalk": "external-crosswalk.example.json", "catalog": "dictionaries/catalog.json"})
    bad = KristalV11ReadViewAdapter(m)
    graph = root / "semantic-graph.example.json"
    payload = json.loads(graph.read_text())
    payload["assertions"][0]["subject"] = "Q8018" # invalid external ID, not a KQ
    graph.write_text(json.dumps(payload), encoding="utf-8")
    before = graph.read_bytes()
    with pytest.raises(AdapterError, match="INVALID_V11_SOURCE"):
        asyncio.run(bad.execute("read", {"locale": "fr-CA", "semantic_ids": ["KQ1001"]}, AdapterContext(operation_id="read")))
    assert graph.read_bytes() == before


@pytest.mark.skipif(not (FRAMEWORK and PACK), reason="requires exact reviewed Framework/Pack checkouts")
def test_real_compiler_context_pack_end_to_end():
    from kompiler.config import AppConfig
    from kompiler.runtime import KompilerRuntime
    from kompiler.protocol.models import QueryPlan

    adapter = real_adapter()
    registry = AdapterRegistry()
    registry.register(adapter)
    rt = KompilerRuntime(AppConfig(), registry, None)
    query = QueryPlan.model_validate({
        "protocol": "kompiler.query", "version": "1.1", "request_id": "v11-integration-demo",
        "operations": [{"id": "read-v11", "target": adapter.target_id, "operation": "read",
                        "params": {"locale": "fr-CA", "semantic_ids": ["KQ1001", "KP2001", "KA3001", "KS4001"]}}],
    })
    result = asyncio.run(rt.run(query))
    assert result.status == "success"
    assert any(record.semantic_id == "KA3001" for record in result.records)
    assert any(record.semantic_id == "KQ1001" for record in result.records)
    assert any(x.source_id.endswith(":KS4001") for x in result.sources)
    assert len(result.relations) == 1




def test_local_only_api_gate(monkeypatch):
    from kompiler.config import AppConfig, ApiConfig
    from kompiler.runtime import KompilerRuntime
    from kompiler.errors import AdmissionError

    class MinimalAdapter:
        adapter_id = "kristal-v11-read-view"

    class FakeRegistry:
        def adapters(self):
            return [MinimalAdapter()]

    import kompiler.runtime as mod
    monkeypatch.setattr(mod, "load_config", lambda _: AppConfig(api=ApiConfig(host="0.0.0.0")))
    monkeypatch.setattr(mod.AdapterRegistry, "from_manifests", lambda _: FakeRegistry())
    with pytest.raises(AdmissionError, match="V11_LOCAL_ONLY"):
        KompilerRuntime.create()
