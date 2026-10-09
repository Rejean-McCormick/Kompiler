from __future__ import annotations

from kompiler.budgeting import select_records
from kompiler.protocol.models import NormalizedRecord, QueryBudget


def _record(identity: str, target: str, text: str) -> NormalizedRecord:
    return NormalizedRecord(record_id=identity, target_id=target, content={"text": text})


def test_lexical_profile_prefers_topic_matches_only_when_truncated():
    records = [
        _record("a", "one", "orchids are plants"),
        _record("b", "one", "electron shells in atoms"),
        _record("c", "one", "atomic structure electron shells"),
    ]
    balanced, cut = select_records(records, QueryBudget(max_items=1, max_bytes=100_000))
    assert cut and [record.record_id for record in balanced] == ["a"]
    lexical, cut = select_records(records, QueryBudget(max_items=1, max_bytes=100_000, selection_mode="lexical"), topic="electrons atomic structure")
    assert cut and [record.record_id for record in lexical] == ["c"]
    complete, cut = select_records(records, QueryBudget(max_items=10, max_bytes=100_000, selection_mode="lexical"), topic="electron")
    assert not cut and complete == records


def test_lexical_profile_still_preserves_target_fairness_and_tie_order():
    records = [
        _record("a", "one", "flower"),
        _record("b", "one", "flower"),
        _record("c", "two", "solar energy"),
        _record("d", "two", "astronomy solar system"),
    ]
    budget = QueryBudget(max_items=2, max_bytes=100_000, selection_mode="lexical")
    first, cut = select_records(records, budget, topic="solar")
    second, _ = select_records(records, budget, topic="solar")
    assert cut and [x.record_id for x in first] == ["a", "c"]
    assert [x.record_id for x in second] == ["a", "c"]


def test_record_byte_budget_is_never_exceeded():
    records = [_record("a", "one", "x"*90), _record("b", "one", "tiny")]
    from kompiler.protocol.canonical import canonical_bytes
    record_bytes = len(canonical_bytes(records[1].model_dump(mode="json", exclude_none=True)))
    selected, cut = select_records(records, QueryBudget(max_items=2, max_bytes=record_bytes + 2))
    assert cut and [r.record_id for r in selected] == ["b"]


def test_default_profile_does_not_change_legacy_query_hash():
    from pathlib import Path
    from kompiler.planner import build_plan
    from kompiler.protocol.canonical import prefixed_hash
    from kompiler.protocol.models import QueryPlan
    from kompiler.registry import AdapterRegistry
    from tests.fixtures.mock_adapter import MockAdapter
    registry = AdapterRegistry()
    registry.register(MockAdapter(Path(".")))
    query = QueryPlan.model_validate({"request_id": "run-new", "topic": "solar", "operations": [
        {"id": "search", "target": "Mock", "operation": "find", "params": {"topic": "solar"}}]})
    old_dump = query.model_dump(by_alias=True, mode="json", exclude_none=True)
    old_dump.pop("request_id")
    old_dump["budget"].pop("selection_mode")
    old_dump["execution"].pop("use_cache")
    old_dump["execution"].pop("max_parallelism")
    assert build_plan(query, registry).query_hash == prefixed_hash("qry", old_dump)
    lexical = query.model_copy(deep=True)
    lexical.budget.selection_mode = "lexical"
    assert build_plan(lexical, registry).query_hash != build_plan(query, registry).query_hash
