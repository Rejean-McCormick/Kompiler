from pathlib import Path

import pytest

from kompiler.config import AppConfig, RuntimeLimits, StorageConfig
from kompiler.protocol.canonical import canonical_bytes
from kompiler.protocol.models import QueryPlan
from kompiler.registry import AdapterRegistry
from kompiler.runtime import KompilerRuntime
from kompiler.storage import SQLiteStore
from tests.fixtures.mock_adapter import MockAdapter


def _runtime(tmp_path: Path, *, retention: str = "metadata", limits: RuntimeLimits | None = None):
    reg = AdapterRegistry()
    reg.register(MockAdapter(tmp_path))
    cfg = AppConfig(
        limits=limits or RuntimeLimits(),
        storage=StorageConfig(database=tmp_path / f"{retention}.db", cache=True, retention=retention),
    )
    return KompilerRuntime(cfg, reg, SQLiteStore(cfg.storage.database))


@pytest.mark.asyncio
async def test_semantic_identity_is_stable_across_reruns(tmp_path: Path):
    rt = _runtime(tmp_path)
    q1 = QueryPlan.model_validate({
        "request_id": "run-a",
        "topic": "air",
        "operations": [{"id": "a", "target": "Mock", "operation": "find", "params": {"topic": "air", "limit": 3}}],
    })
    q2 = q1.model_copy(update={"request_id": "run-b"})
    p1 = await rt.run(q1)
    p2 = await rt.run(q2)
    assert p1.context_pack_id == p2.context_pack_id
    assert p1.semantic_hash == p2.semantic_hash
    assert p1.execution.cache_hits == 0
    assert p2.execution.cache_hits == 1
    assert p1.artifact_hash != p2.artifact_hash


@pytest.mark.asyncio
async def test_cache_key_includes_effective_operation_budget(tmp_path: Path):
    rt = _runtime(tmp_path)
    q1 = QueryPlan.model_validate({
        "request_id": "small", "topic": "air",
        "operations": [{
            "id": "a", "target": "Mock", "operation": "find",
            "params": {"topic": "air", "limit": 5}, "budget": {"max_items": 1},
        }],
    })
    q2 = QueryPlan.model_validate({
        "request_id": "large", "topic": "air",
        "operations": [{
            "id": "a", "target": "Mock", "operation": "find",
            "params": {"topic": "air", "limit": 5}, "budget": {"max_items": 5},
        }],
    })
    p1 = await rt.run(q1)
    p2 = await rt.run(q2)
    assert p1.summary.record_count == 1
    assert p2.summary.record_count == 5
    assert p2.execution.cache_hits == 0


@pytest.mark.asyncio
async def test_metadata_retention_does_not_persist_pack(tmp_path: Path):
    rt = _runtime(tmp_path, retention="metadata")
    q = QueryPlan.model_validate({
        "request_id": "metadata",
        "operations": [{"id": "a", "target": "Mock", "operation": "find", "params": {"topic": "air"}}],
    })
    pack = await rt.run(q)
    run = rt.store.get_run(pack.execution.run_id)
    assert run is not None
    assert run["context_pack_id"] == pack.context_pack_id
    assert run["artifact_id"] is None
    assert rt.store.get_artifact(pack.artifact_hash) is None


@pytest.mark.asyncio
async def test_pack_retention_uses_artifact_hash(tmp_path: Path):
    rt = _runtime(tmp_path, retention="packs")
    q = QueryPlan.model_validate({
        "request_id": "packs",
        "operations": [{"id": "a", "target": "Mock", "operation": "find", "params": {"topic": "air"}}],
    })
    pack = await rt.run(q)
    run = rt.store.get_run(pack.execution.run_id)
    assert run["artifact_id"] == pack.artifact_hash
    assert rt.store.get_artifact(pack.artifact_hash)["context_pack_id"] == pack.context_pack_id


@pytest.mark.asyncio
async def test_join_limit_fails_operation_closed(tmp_path: Path):
    limits = RuntimeLimits(max_join_items=1)
    rt = _runtime(tmp_path, limits=limits)
    q = QueryPlan.model_validate({
        "request_id": "join-limit",
        "operations": [
            {"id": "a", "target": "Mock", "operation": "find", "params": {"topic": "air", "limit": 3}},
            {
                "id": "b", "target": "Mock", "operation": "echo_inputs", "params": {"values": []},
                "inputs": [{"from": "a", "selector": "$.records[*].source_record_ref", "inject_as": "values"}],
            },
        ],
    })
    pack = await rt.run(q)
    receipt = next(r for r in pack.execution.receipts if r.operation_id == "b")
    assert receipt.status == "failed"
    assert receipt.error_code == "RESOURCE_LIMIT_EXCEEDED"
    assert pack.status == "partial"


@pytest.mark.asyncio
async def test_total_context_pack_byte_budget_is_enforced(tmp_path: Path):
    rt = _runtime(tmp_path)
    q = QueryPlan.model_validate({
        "request_id": "bounded",
        "topic": "air",
        "budget": {"max_items": 50, "max_bytes": 9000, "target_tokens": 100000},
        "operations": [{"id": "a", "target": "Mock", "operation": "find", "params": {"topic": "air", "limit": 50}}],
    })
    pack = await rt.run(q)
    assert len(canonical_bytes(pack.model_dump(by_alias=True, mode="json", exclude_none=True))) <= 9000
    assert pack.summary.truncated is True
    assert pack.summary.record_count < 50


@pytest.mark.asyncio
async def test_empty_status_and_parent_context_are_preserved(tmp_path: Path):
    rt = _runtime(tmp_path)
    q = QueryPlan.model_validate({
        "request_id": "empty",
        "parent_context_pack_id": "ctx:sha256:parent",
        "operations": [{"id": "a", "target": "Mock", "operation": "echo_inputs", "params": {"values": []}}],
    })
    pack = await rt.run(q)
    assert pack.status == "empty"
    assert pack.parent_context_pack_id == "ctx:sha256:parent"

@pytest.mark.asyncio
async def test_conflicts_can_surface_across_targets_with_shared_external_ids(tmp_path: Path):
    from kompiler.adapters.base import Adapter, AdapterContext, AdapterResult
    from kompiler.adapters.common import opcap
    from kompiler.protocol.models import SourceDescriptor

    class A(Adapter):
        adapter_id="a"; adapter_version="1"; target_id="A"; root=tmp_path
        def capabilities(self): return [opcap("find","x",{})]
        def source_descriptor(self): return SourceDescriptor(state_id="sha256:a")
        async def execute(self, operation, params, context):
            return AdapterResult(items=[{"id":"a1","statement":{"subject":{"external_id":"urn:s"},"predicate":{"external_id":"urn:p"},"object":{"value":1}}}])
    class B(Adapter):
        adapter_id="b"; adapter_version="1"; target_id="B"; root=tmp_path
        def capabilities(self): return [opcap("find","x",{})]
        def source_descriptor(self): return SourceDescriptor(state_id="sha256:b")
        async def execute(self, operation, params, context):
            return AdapterResult(items=[{"id":"b1","statement":{"subject":{"external_id":"urn:s"},"predicate":{"external_id":"urn:p"},"object":{"value":2}}}])

    reg=AdapterRegistry(); reg.register(A()); reg.register(B())
    cfg=AppConfig(storage=StorageConfig(database=tmp_path/"conflict.db",cache=False))
    rt=KompilerRuntime(cfg,reg,SQLiteStore(cfg.storage.database))
    q=QueryPlan.model_validate({"request_id":"conf","operations":[{"id":"a","target":"A","operation":"find"},{"id":"b","target":"B","operation":"find"}]})
    pack=await rt.run(q)
    assert pack.summary.conflict_count == 1
    assert len(pack.conflicts) == 1

@pytest.mark.asyncio
async def test_compilation_failure_marks_run_failed(tmp_path: Path):
    from kompiler.errors import CompilationError

    rt = _runtime(tmp_path)
    q = QueryPlan.model_validate({
        "request_id": "budget-impossible",
        "budget": {"max_items": 1, "max_bytes": 1, "target_tokens": 1},
        "operations": [{"id": "a", "target": "Mock", "operation": "echo_inputs", "params": {"values": []}}],
    })
    with pytest.raises(CompilationError) as exc_info:
        await rt.run(q, run_id="run:budget-impossible")
    assert exc_info.value.code == "BUDGET_IMPOSSIBLE"
    row = rt.store.get_run("run:budget-impossible")
    assert row is not None
    assert row["status"] == "failed"
    assert row["metadata"]["error"]["error"]["code"] == "BUDGET_IMPOSSIBLE"
