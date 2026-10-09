from __future__ import annotations

import json
import unicodedata
from typing import Any

from kompiler.adapters.base import AdapterContext, AdapterResult
from kompiler.protocol.models import OperationCapability

from .common import KristalAdapterBase, infer_schema_version, opcap


def _norm(s: Any) -> str:
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()


class HospitalOpsAdapter(KristalAdapterBase):
    adapter_id = "kristal-hospitalops"
    adapter_version = "1.0.0"
    target_id = "HospitalOps"

    def __init__(self, root):
        super().__init__(root)
        state = self.root / "knowledge-base/clinical-commons.structured-epistemic-state.json"
        self.schema_version = infer_schema_version(state)
        self.identity_paths = [
            state,
            self.root / "knowledge-sources/hospitalops_glossaire_v1.json",
            *sorted((self.root / "knowledge-sources").glob("*.json")),
        ]

    def capabilities(self) -> list[OperationCapability]:
        s={"type":"string"}; lim={"type":"integer","minimum":1,"maximum":5000}
        return [
            opcap("glossary", "Search the HospitalOps bilingual glossary.", {"query":s,"family":s,"limit":lim}),
            opcap("assertions", "Search the HospitalOps clinical commons structured state.", {"text":s,"limit":lim}, max_items=5000, record_kinds=["assertion", "relation"]),
            opcap("knowledge_source", "Return a named HospitalOps knowledge-source document.", {"name": {"type":"string","enum":["access_governance","clinical_invariants","clinical_pathways","cryptographic_architecture","data_domains","metric_definitions","practice_event_taxonomy","resource_capabilities","role_capabilities","terminology_mappings","upstream_artifacts"]}}, ["name"]),
        ]

    async def execute(self, operation: str, params: dict[str, Any], context: AdapterContext) -> AdapterResult:
        self.validate_params(operation, params)
        limit=min(int(params.get("limit", context.max_items or 1000)), context.max_items or 5000)
        if operation=="glossary":
            rows=self.read_json("knowledge-sources/hospitalops_glossaire_v1.json").get("terms",[])
            if params.get("family"): rows=[x for x in rows if x.get("family")==params["family"]]
            if params.get("query"):
                q=_norm(params["query"]); rows=[x for x in rows if q in _norm(" ".join([x.get("id",""),x.get("term_fr",""),x.get("term_en",""),x.get("definition","")," ".join(x.get("aliases",[]))]))]
        elif operation=="assertions":
            rows=self.read_json("knowledge-base/clinical-commons.structured-epistemic-state.json").get("assertions",[])
            if params.get("text"): rows=[x for x in rows if _norm(params["text"]) in _norm(json.dumps(x,ensure_ascii=False))]
        elif operation=="knowledge_source": rows=[self.read_json(f"knowledge-sources/{params['name']}.json")]
        else: raise AssertionError(operation)
        return AdapterResult(items=rows[:limit],raw_item_count=len(rows),truncated=len(rows)>limit)
