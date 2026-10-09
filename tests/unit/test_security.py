from pathlib import Path

import pytest

from kompiler.adapters.common import KristalAdapterBase, opcap
from kompiler.errors import AdapterError, AdmissionError
from kompiler.planner import build_plan
from kompiler.protocol.models import QueryPlan
from kompiler.registry import AdapterRegistry
from tests.fixtures.mock_adapter import MockAdapter


class FileAdapter(KristalAdapterBase):
    adapter_id="file"; adapter_version="1"; target_id="File"
    def capabilities(self): return [opcap("noop","noop",{})]
    async def execute(self, operation, params, context): raise NotImplementedError


def test_path_traversal_is_rejected(tmp_path: Path):
    root=tmp_path/"root"; root.mkdir()
    outside=tmp_path/"outside.json"; outside.write_text("{}")
    adapter=FileAdapter(root)
    with pytest.raises(AdapterError) as exc:
        adapter.read_json("../outside.json")
    assert exc.value.code == "PATH_OUTSIDE_ALLOWED_ROOT"


def test_symlink_escape_is_rejected(tmp_path: Path):
    root=tmp_path/"root"; root.mkdir()
    outside=tmp_path/"outside.json"; outside.write_text("{}")
    link=root/"link.json"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlinks unavailable")
    adapter=FileAdapter(root)
    with pytest.raises(AdapterError) as exc:
        adapter.read_json("link.json")
    assert exc.value.code == "PATH_OUTSIDE_ALLOWED_ROOT"


def test_capability_snapshot_mismatch_is_rejected(tmp_path: Path):
    reg=AdapterRegistry(); reg.register(MockAdapter(tmp_path))
    q=QueryPlan.model_validate({
        "request_id":"snap",
        "capability_snapshot_id":"cap:sha256:not-current",
        "operations":[{"id":"a","target":"Mock","operation":"find","params":{"topic":"air"}}],
    })
    with pytest.raises(AdmissionError) as exc:
        build_plan(q,reg)
    assert exc.value.code == "CAPABILITY_SNAPSHOT_MISMATCH"
