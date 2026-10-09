from __future__ import annotations

from typing import Any

from kompiler.adapters.base import AdapterContext, AdapterResult
from kompiler.protocol.models import OperationCapability

from .common import KristalAdapterBase, infer_schema_version, opcap
from .utils import run_python_json


class MathAdapter(KristalAdapterBase):
    adapter_id = "kristal-math"
    adapter_version = "1.0.0"
    target_id = "Math"

    def __init__(self, root):
        super().__init__(root)
        state = self.root / "corpus/math.structured-epistemic-state.json"
        self.schema_version = infer_schema_version(state)
        self.identity_paths = [state, self.root / "corpus/reverse-index.json", self.root / "tools/query.py"]

    def capabilities(self) -> list[OperationCapability]:
        s = {"type": "string"}
        return [opcap("find", "Filter mathematical assertions using Kristal indexes.", {
            "subject": s, "predicate": s, "certainty": s, "status": s, "role": s,
            "neighbors": s, "domain": s, "context": s,
            "limit": {"type": "integer", "minimum": 1, "maximum": 5000},
        }, record_kinds=["assertion", "relation"], max_items=5000)]

    async def execute(self, operation: str, params: dict[str, Any], context: AdapterContext) -> AdapterResult:
        self.validate_params(operation, params)
        args: list[str] = []
        for key in ["subject", "predicate", "certainty", "status", "role", "neighbors", "domain", "context"]:
            if params.get(key) is not None:
                args += [f"--{key}", str(params[key])]
        args += ["--limit", str(min(int(params.get("limit", context.max_items or 100)), context.max_items or 5000))]
        return await run_python_json(self.root, self.root / "tools/query.py", args, timeout_ms=context.timeout_ms, max_bytes=context.max_stdout_bytes)
