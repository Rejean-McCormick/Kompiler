from __future__ import annotations

from typing import Any

from kompiler.adapters.base import Adapter, AdapterContext, AdapterResult
from kompiler.protocol.models import OperationCapability, SourceDescriptor
from kompiler.adapters.common import opcap


class MockAdapter(Adapter):
    adapter_id="mock-kristal"; adapter_version="1.0.0"; target_id="Mock"; kind="kristal"
    def __init__(self,root): self.root=root
    def source_descriptor(self): return SourceDescriptor(kristal_schema_version="6.0",state_id="sha256:mock",root_hint="mock")
    def capabilities(self)->list[OperationCapability]:
        return [
            opcap("find","Return synthetic assertions.",{"topic":{"type":"string"},"limit":{"type":"integer","minimum":1,"maximum":100}},["topic"],max_items=100,record_kinds=["assertion"]),
            opcap("echo_inputs","Return upstream inputs.",{"values":{"type":"array"}},["values"]),
        ]
    async def execute(self,operation:str,params:dict[str,Any],context:AdapterContext)->AdapterResult:
        if operation=="find":
            rows=[]
            for i in range(min(params.get("limit",3),100)):
                rows.append({"source_assertion_id":f"M{i+1}","assertion_status":"sourced","certainty_level":"high","statement":{"subject":{"external_id":f"urn:mock:{params['topic']}","label":params['topic']},"predicate":{"external_id":"mock:has_value","label":"has value"},"object":{"kind":"value","value":i}}})
            return AdapterResult(items=rows)
        if operation=="echo_inputs": return AdapterResult(items=[{"id":str(i),"value":x} for i,x in enumerate(params["values"])])
        raise ValueError(operation)
