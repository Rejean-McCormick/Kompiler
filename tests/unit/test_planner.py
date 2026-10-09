from pathlib import Path

import pytest

from kompiler.errors import AdmissionError
from kompiler.planner import build_plan
from kompiler.protocol.models import QueryPlan
from kompiler.registry import AdapterRegistry
from tests.fixtures.mock_adapter import MockAdapter


def registry():
    r=AdapterRegistry(); r.register(MockAdapter(Path("."))); return r


def test_dag_stages():
    q=QueryPlan.model_validate({"request_id":"x","operations":[{"id":"a","target":"Mock","operation":"find","params":{"topic":"air"}},{"id":"b","target":"Mock","operation":"echo_inputs","params":{"values":[]},"inputs":[{"from":"a","selector":"$.records[*].source_record_ref"}]}]})
    p=build_plan(q,registry()); assert p.stages==[["a"],["b"]]


def test_cycle_rejected():
    q=QueryPlan.model_validate({"request_id":"x","operations":[{"id":"a","target":"Mock","operation":"find","params":{"topic":"a"},"inputs":[{"from":"b"}]},{"id":"b","target":"Mock","operation":"find","params":{"topic":"b"},"inputs":[{"from":"a"}]}]})
    with pytest.raises(AdmissionError) as e: build_plan(q,registry())
    assert e.value.code=="CYCLIC_PLAN"
