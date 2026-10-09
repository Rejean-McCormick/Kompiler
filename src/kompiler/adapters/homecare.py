from __future__ import annotations

from typing import Any

from kompiler.adapters.base import AdapterContext, AdapterResult
from kompiler.protocol.models import OperationCapability

from .common import KristalAdapterBase, opcap
from .utils import run_python_json


class HomeCareAdapter(KristalAdapterBase):
    adapter_id = "kristal-homecare"
    adapter_version = "1.0.0"
    target_id = "HomeCare"

    def __init__(self, root):
        super().__init__(root)
        self.schema_version = "2.0"
        self.identity_paths = [
            self.root / "manifest.sha256.json",
            self.root / "tools/query.py",
            self.root / "examples/demo-home/projections/current-state.json",
        ]

    def capabilities(self) -> list[OperationCapability]:
        s = {"type": "string"}
        return [
            opcap("overview", "Return synthetic demo-home overview.", {}),
            opcap("due", "Return due maintenance projection for demo-home.", {}),
            opcap("history", "Return event history for a demo-home asset.", {"asset_id": s}, ["asset_id"]),
            opcap("paths", "Return demo-home dependency paths.", {}),
            opcap("gaps", "Return demo-home knowledge gaps.", {}),
            opcap("diagnose", "Return a diagnostic projection for an observation.", {"observation_id": s}, ["observation_id"]),
        ]

    async def execute(self, operation: str, params: dict[str, Any], context: AdapterContext) -> AdapterResult:
        self.validate_params(operation, params)
        args = ["--demo"]
        if operation in {"overview", "due", "paths", "gaps"}: args.append(f"--{operation}")
        elif operation == "history": args += ["--history", str(params["asset_id"])]
        elif operation == "diagnose": args += ["--diagnose", str(params["observation_id"])]
        else: raise AssertionError(operation)
        return await run_python_json(self.root, self.root / "tools/query.py", args, timeout_ms=context.timeout_ms, max_bytes=context.max_stdout_bytes)
