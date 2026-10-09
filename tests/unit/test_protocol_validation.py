import pytest
from pydantic import ValidationError

from kompiler.protocol.models import QueryPlan


def test_query_requires_at_least_one_operation():
    with pytest.raises(ValidationError):
        QueryPlan.model_validate({"request_id": "q", "operations": []})


def test_query_rejects_empty_identifiers():
    cases = [
        {"request_id": "", "operations": [{"id": "a", "target": "Mock", "operation": "find"}]},
        {"request_id": "q", "operations": [{"id": "", "target": "Mock", "operation": "find"}]},
        {"request_id": "q", "operations": [{"id": "a", "target": "", "operation": "find"}]},
        {"request_id": "q", "operations": [{"id": "a", "target": "Mock", "operation": ""}]},
    ]
    for body in cases:
        with pytest.raises(ValidationError):
            QueryPlan.model_validate(body)
