from pathlib import Path

import pytest

from kompiler.adapters.base import Adapter, AdapterContext, AdapterResult
from kompiler.adapters.common import opcap
from kompiler.config import AppConfig
from kompiler.errors import AdmissionError
from kompiler.planner import build_plan
from kompiler.protocol.models import QueryPlan, SourceDescriptor
from kompiler.registry import AdapterRegistry


class NetworkAdapter(Adapter):
    adapter_id = "network-test"
    adapter_version = "1.0"
    target_id = "Network"
    root = Path(".")

    def capabilities(self):
        return [opcap("fetch", "network op", {}, network=True)]

    def source_descriptor(self):
        return SourceDescriptor(state_id="sha256:network-test")

    async def execute(self, operation: str, params: dict, context: AdapterContext):
        return AdapterResult()


def test_network_operation_is_denied_by_default():
    reg = AdapterRegistry()
    reg.register(NetworkAdapter())
    q = QueryPlan.model_validate({"request_id": "x", "operations": [{"id": "n", "target": "Network", "operation": "fetch"}]})
    with pytest.raises(AdmissionError) as exc:
        build_plan(q, reg, config=AppConfig())
    assert exc.value.code == "NETWORK_DENIED"


def test_network_operation_can_be_admitted_by_runtime_policy():
    reg = AdapterRegistry()
    reg.register(NetworkAdapter())
    q = QueryPlan.model_validate({"request_id": "x", "operations": [{"id": "n", "target": "Network", "operation": "fetch"}]})
    plan = build_plan(q, reg, config=AppConfig(network_default="allow"))
    assert plan.stages == [["n"]]
