from __future__ import annotations

from pathlib import Path
from typing import Any

import jsonschema
from pydantic import ValidationError

from .models import CapabilitySnapshot, ContextPack, ErrorArtifact, QueryPlan

MODELS = {
    "kompiler.capabilities": CapabilitySnapshot,
    "kompiler.query": QueryPlan,
    "kompiler.context-pack": ContextPack,
    "kompiler.error": ErrorArtifact,
}

SCHEMA_FILES = {
    "kompiler.capabilities": "kompiler-capabilities.schema.json",
    "kompiler.query": "kompiler-query.schema.json",
    "kompiler.context-pack": "kompiler-context-pack.schema.json",
    "kompiler.error": "kompiler-error.schema.json",
}


def detect_protocol(data: dict[str, Any]) -> str:
    proto = data.get("protocol")
    if proto not in MODELS:
        raise ValueError(f"unsupported protocol: {proto!r}")
    return str(proto)


def validate_model(data: dict[str, Any]):
    model = MODELS[detect_protocol(data)]
    return model.model_validate(data)


def validate_json_schema(data: dict[str, Any], schema_root: str | Path) -> None:
    proto = detect_protocol(data)
    import json

    schema = json.loads((Path(schema_root) / SCHEMA_FILES[proto]).read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(data)


def format_validation_error(exc: ValidationError) -> list[dict[str, Any]]:
    return [
        {"path": ".".join(str(x) for x in e["loc"]), "message": e["msg"], "type": e["type"]}
        for e in exc.errors()
    ]
