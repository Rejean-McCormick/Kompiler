from __future__ import annotations

from typing import Any

from kompiler.adapters.base import AdapterContext, AdapterResult
from kompiler.protocol.models import OperationCapability

from .common import KristalAdapterBase, opcap
from .utils import run_python_json


class CathoAdapter(KristalAdapterBase):
    adapter_id = "kristal-catho"
    adapter_version = "1.0.0"
    target_id = "Catho"

    def __init__(self, root):
        super().__init__(root)
        self.schema_version = "1.0"
        self.identity_paths = [
            self.root / "canonical-corpus/corpus-chretien.semantic.json",
            self.root / "manifest.sha256.json",
            self.root / "tools/query.py",
        ]

    def capabilities(self) -> list[OperationCapability]:
        s = {"type": "string"}
        return [opcap("find", "Filter curated Christian corpus assertions by author, theme, identity, or semantic class.", {
            "author": s, "theme": s, "id": s, "dogmas": {"type": "boolean"},
            "relations": {"type": "boolean"}, "arguments": {"type": "boolean"},
        }, record_kinds=["assertion", "relation"])]

    async def execute(self, operation: str, params: dict[str, Any], context: AdapterContext) -> AdapterResult:
        self.validate_params(operation, params)
        args: list[str] = []
        for k in ["author", "theme", "id"]:
            if params.get(k): args += [f"--{k}", str(params[k])]
        for k in ["dogmas", "relations", "arguments"]:
            if params.get(k): args.append(f"--{k}")
        args.append("--json")
        return await run_python_json(self.root, self.root / "tools/query.py", args, timeout_ms=context.timeout_ms, max_bytes=context.max_stdout_bytes)
