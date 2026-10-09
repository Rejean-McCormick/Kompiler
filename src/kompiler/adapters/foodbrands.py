from __future__ import annotations

import json
from typing import Any

from kompiler.adapters.base import AdapterContext, AdapterResult
from kompiler.protocol.models import OperationCapability

from .common import KristalAdapterBase, opcap


class FoodBrandsAdapter(KristalAdapterBase):
    adapter_id = "kristal-foodbrands"
    adapter_version = "1.0.0"
    target_id = "FoodBrands"

    def __init__(self, root):
        super().__init__(root)
        self.schema_version = "source-library"
        self.identity_paths = [
            self.root / "source-catalog/providers.json",
            self.root / "source-catalog/reference-sources.json",
            self.root / "source-catalog/acquisition-overrides.json",
        ]

    def capabilities(self) -> list[OperationCapability]:
        s={"type":"string"}
        return [
            opcap("providers", "Search configured food-brand source providers.", {"text":s,"limit":{"type":"integer","minimum":1,"maximum":5000}}),
            opcap("reference_sources", "Search food-brand reference source catalog.", {"text":s,"limit":{"type":"integer","minimum":1,"maximum":5000}}),
            opcap("acquisition_overrides", "Return source acquisition overrides.", {}),
        ]

    async def execute(self, operation: str, params: dict[str, Any], context: AdapterContext) -> AdapterResult:
        self.validate_params(operation,params)
        if operation=="providers": obj=self.read_json("source-catalog/providers.json")
        elif operation=="reference_sources": obj=self.read_json("source-catalog/reference-sources.json")
        elif operation=="acquisition_overrides": return AdapterResult(items=[self.read_json("source-catalog/acquisition-overrides.json")])
        else: raise AssertionError(operation)
        rows = obj if isinstance(obj,list) else next((v for v in obj.values() if isinstance(v,list)), [obj])
        if params.get("text"):
            q=params["text"].lower(); rows=[x for x in rows if q in json.dumps(x,ensure_ascii=False).lower()]
        limit=min(int(params.get("limit",context.max_items or 1000)),context.max_items or 5000)
        return AdapterResult(items=rows[:limit],raw_item_count=len(rows),truncated=len(rows)>limit)
