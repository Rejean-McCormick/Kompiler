from pathlib import Path

import pytest

from kompiler.config import AppConfig, StorageConfig
from kompiler.protocol.models import QueryPlan
from kompiler.registry import AdapterRegistry
from kompiler.runtime import KompilerRuntime
from kompiler.storage import SQLiteStore
from tests.fixtures.mock_adapter import MockAdapter


@pytest.mark.asyncio
async def test_end_to_end_context_pack(tmp_path:Path):
    reg=AdapterRegistry(); reg.register(MockAdapter(tmp_path))
    cfg=AppConfig(storage=StorageConfig(database=tmp_path/"k.db",cache=True))
    rt=KompilerRuntime(cfg,reg,SQLiteStore(cfg.storage.database))
    q=QueryPlan.model_validate({"request_id":"demo","topic":"air","operations":[{"id":"a","target":"Mock","operation":"find","params":{"topic":"air","limit":3}}]})
    pack=await rt.run(q)
    assert pack.protocol=="kompiler.context-pack"
    assert pack.summary.record_count==3
    assert pack.summary.referent_count==1
    assert pack.execution.receipts[0].status=="success"
    pack2=await rt.run(q)
    assert pack2.execution.cache_hits==1
