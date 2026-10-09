from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kompiler.protocol.models import CapabilitySnapshot, ContextPack, ErrorArtifact, QueryPlan

OUT = ROOT / "schemas"
OUT.mkdir(exist_ok=True)
MODELS = {
    "kompiler-capabilities.schema.json": CapabilitySnapshot,
    "kompiler-query.schema.json": QueryPlan,
    "kompiler-context-pack.schema.json": ContextPack,
    "kompiler-error.schema.json": ErrorArtifact,
}
for name, model in MODELS.items():
    schema = model.model_json_schema(mode="validation")
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    (OUT / name).write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(name)
