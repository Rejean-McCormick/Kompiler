import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parents[2]


def test_query_example_conforms():
    schema=json.loads((ROOT/"schemas/kompiler-query.schema.json").read_text())
    query=json.loads((ROOT/"examples/queries/pollution.json").read_text())
    Draft202012Validator(schema).validate(query)
