from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import Adapter, AdapterContext, AdapterResult
from .common import opcap
from kompiler.protocol.models import OperationCapability, SourceDescriptor


class SelfTestAdapter(Adapter):
    adapter_id="kompiler-selftest"; adapter_version="1.0.0"; target_id="SelfTest"; kind="synthetic"
    def __init__(self): self.root=Path.cwd()
    def source_descriptor(self)->SourceDescriptor: return SourceDescriptor(kristal_schema_version="synthetic",state_id="sha256:selftest",integrity="synthetic")
    def capabilities(self)->list[OperationCapability]:
        return [opcap("facts","Emit deterministic synthetic assertions.",{"topic":{"type":"string"}},["topic"],record_kinds=["assertion"])]
    async def execute(self,operation:str,params:dict[str,Any],context:AdapterContext)->AdapterResult:
        topic=params["topic"]
        return AdapterResult(items=[
            {"source_assertion_id":"S1","assertion_status":"sourced","statement":{"subject":{"external_id":f"urn:selftest:{topic}","label":topic},"predicate":{"external_id":"selftest:has_state","label":"has state"},"object":{"kind":"value","value":"ready"}}},
            {"source_assertion_id":"S2","assertion_status":"sourced","statement":{"subject":{"external_id":f"urn:selftest:{topic}","label":topic},"predicate":{"external_id":"selftest:has_state","label":"has state"},"object":{"kind":"value","value":"verified"}}}
        ])
