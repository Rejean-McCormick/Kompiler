"""C5: use the *real* Zoology snapshot locally without making publication claims."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from kompiler.adapters.kristal_v9 import KristalV9StateAdapter
from kompiler.config import AppConfig, StorageConfig
from kompiler.kristal_standard import configure_standard_root
from kompiler.protocol.models import QueryPlan
from kompiler.registry import AdapterRegistry
from kompiler.runtime import KompilerRuntime

STATE_DIGEST = "sha256:2503493eed8b2515107f9c32eed48286845f5468838ad3ae7b4a8f66a65f2ac8"


@pytest.mark.asyncio
async def test_real_zoology_is_read_only_context_pack(tmp_path):
    root = os.getenv("C5_ZOOLOGY_ROOT")
    framework = os.getenv("C5_FRAMEWORK_ROOT")
    if not root or not framework:
        pytest.skip("set C5_ZOOLOGY_ROOT and C5_FRAMEWORK_ROOT to test real files")
    configure_standard_root(Path(framework))
    before = {
        "workspace": hashlib.sha256((Path(root) / "kristal.workspace.json").read_bytes()).hexdigest(),
        "state": hashlib.sha256((Path(root) / ".kristal/v9/state-snapshot.json").read_bytes()).hexdigest(),
        "canon": hashlib.sha256((Path(root) / "canon/domain/legacy-v6-state.payload.json").read_bytes()).hexdigest(),
    }
    adapter = KristalV9StateAdapter(Path(root))
    assert adapter.health()["ok"] is True
    registry = AdapterRegistry()
    registry.register(adapter)
    runtime = KompilerRuntime(AppConfig(storage=StorageConfig(database=tmp_path / "c5.db", cache=False)), registry, None)
    plan = QueryPlan.model_validate({
        "request_id": "c5-zoology-state", "topic": "zoology", "operations": [{
            "id": "read-zoology", "target": adapter.target_id, "operation": "state", "params": {},
        }],
    })
    pack = await runtime.run(plan)
    assert pack.protocol == "kompiler.context-pack"
    assert pack.summary.record_count == 1
    assert all(receipt.status == "success" for receipt in pack.execution.receipts)
    assert any(STATE_DIGEST in str(record.model_dump()) for record in pack.records)
    assert all(cap.semantics.read_only for cap in adapter.capabilities())
    after = {
        "workspace": hashlib.sha256((Path(root) / "kristal.workspace.json").read_bytes()).hexdigest(),
        "state": hashlib.sha256((Path(root) / ".kristal/v9/state-snapshot.json").read_bytes()).hexdigest(),
        "canon": hashlib.sha256((Path(root) / "canon/domain/legacy-v6-state.payload.json").read_bytes()).hexdigest(),
    }
    assert before == after
