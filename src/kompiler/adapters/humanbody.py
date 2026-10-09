from __future__ import annotations

import json
import unicodedata
from typing import Any

from kompiler.adapters.base import AdapterContext, AdapterResult
from kompiler.protocol.models import OperationCapability

from .common import KristalAdapterBase, infer_schema_version, opcap


def _norm(x: Any) -> str:
    return unicodedata.normalize("NFKD", str(x)).encode("ascii", "ignore").decode().lower()


def _tail(v: Any) -> Any:
    return v.rsplit(":", 1)[-1] if isinstance(v, str) else v


def _qvals(x: dict[str, Any], pid: str) -> list[Any]:
    out = []
    for q in x.get("statement", {}).get("qualifiers", []):
        if q.get("predicate", {}).get("external_id") != pid:
            continue
        o = q.get("object", {})
        v = o.get("value")
        if o.get("kind") == "item" and isinstance(v, dict):
            out.append(v.get("external_id") or v.get("label"))
        else:
            out.append(v)
    return out


class HumanBodyAdapter(KristalAdapterBase):
    adapter_id = "kristal-humanbody"
    adapter_version = "1.0.0"
    target_id = "HumanBody"

    def __init__(self, root):
        super().__init__(root)
        state = self.root / "corpus/humanbody.structured-epistemic-state.json"
        self.schema_version = infer_schema_version(state)
        self.identity_paths = [
            state,
            self.root / "corpus/index.json",
            self.root / "corpus/pathways.json",
            self.root / "corpus/feedback-loops.json",
            self.root / "corpus/glossary.json",
            self.root / "corpus/coverage-report.json",
            self.root / "corpus/tension-report.json",
            self.root / "corpus/density-report.json",
            self.root / "corpus/depth-report.json",
            self.root / "corpus/corroboration-report.json",
            self.root / "corpus/process-coupling-report.json",
            self.root / "corpus/enrichment-frontier.json",
        ]

    def capabilities(self) -> list[OperationCapability]:
        s = {"type": "string"}
        find_props = {
            "text": s, "family": s, "predicate": s, "layer": s, "scale": s,
            "process": s, "anatomy": s, "physiological_state": s, "pathological_state": s,
            "timescale": s, "source_layer": s, "target_layer": s, "source": s,
            "assertion_status": s, "evidence_status": s, "ontology_system": s,
            "cross_layer": {"type": "boolean"}, "cross_scale": {"type": "boolean"},
            "mapped": {"type": "boolean"}, "limit": {"type": "integer", "minimum": 1, "maximum": 5000},
        }
        return [
            opcap("find", "Filter HumanBody structured epistemic assertions.", find_props, max_items=5000, record_kinds=["assertion", "relation"]),
            opcap("pathways", "Return mechanism/pathway projections, optionally matching one pathway.", {"query": s, "limit": {"type": "integer", "minimum": 1, "maximum": 1000}}),
            opcap("feedback_loops", "Return feedback-loop projections, optionally matching one loop.", {"query": s, "limit": {"type": "integer", "minimum": 1, "maximum": 1000}}),
            opcap("glossary", "Search the HumanBody glossary.", {"text": s, "category": s, "limit": {"type": "integer", "minimum": 1, "maximum": 5000}}),
            opcap("coverage", "Return HumanBody coverage report.", {}),
            opcap("tensions", "Return candidate epistemic tensions.", {"limit": {"type": "integer", "minimum": 1, "maximum": 5000}}),
            opcap("density", "Return process density report.", {"limit": {"type": "integer", "minimum": 1, "maximum": 5000}}),
            opcap("depth", "Return process depth report.", {"limit": {"type": "integer", "minimum": 1, "maximum": 5000}}),
            opcap("corroboration", "Return process corroboration report.", {"limit": {"type": "integer", "minimum": 1, "maximum": 5000}}),
            opcap("coupling", "Return process coupling report.", {"limit": {"type": "integer", "minimum": 1, "maximum": 5000}}),
            opcap("frontier", "Return enrichment frontier.", {"limit": {"type": "integer", "minimum": 1, "maximum": 5000}}),
        ]

    async def execute(self, operation: str, params: dict[str, Any], context: AdapterContext) -> AdapterResult:
        self.validate_params(operation, params)
        limit = min(int(params.get("limit", context.max_items or 1000)), context.max_items or 5000)
        if operation == "find":
            state = self.read_json("corpus/humanbody.structured-epistemic-state.json")
            index = self.read_json("corpus/index.json")
            cross_l, cross_s = set(index.get("cross_layer", [])), set(index.get("cross_scale", []))
            mapped_ids: set[str] = set()
            if params.get("mapped"):
                for ids in index.get("by_ontology_system", {}).values(): mapped_ids.update(ids)
            source_ids = set(index.get("by_source", {}).get(params["source"], [])) if params.get("source") else None
            evidence_ids = set(index.get("by_evidence_status", {}).get(params["evidence_status"], [])) if params.get("evidence_status") else None
            ontology_ids = set(index.get("by_ontology_system", {}).get(params["ontology_system"], [])) if params.get("ontology_system") else None
            out = []
            for x in state.get("assertions", []):
                if params.get("family") and params["family"] not in _qvals(x, "humanbody:family"): continue
                if params.get("predicate") and x.get("statement", {}).get("predicate", {}).get("external_id") not in {params["predicate"], "humanbody:" + params["predicate"], "urn:humanbody:predicate:" + params["predicate"]}: continue
                layers = {_tail(v) for v in _qvals(x, "humanbody:source_layer") + _qvals(x, "humanbody:target_layer") + _qvals(x, "humanbody:involved_layer")}
                scales = {_tail(v) for v in _qvals(x, "humanbody:source_scale") + _qvals(x, "humanbody:target_scale")}
                if params.get("layer") and params["layer"] not in layers: continue
                if params.get("scale") and params["scale"] not in scales: continue
                if params.get("process") and params["process"] not in {_tail(v) for v in _qvals(x, "humanbody:process")}: continue
                if params.get("anatomy") and _norm(params["anatomy"]) not in _norm(json.dumps(_qvals(x, "humanbody:anatomical_context"), ensure_ascii=False)): continue
                for key, pid in [("physiological_state", "humanbody:physiological_state"), ("pathological_state", "humanbody:pathological_state"), ("timescale", "humanbody:timescale"), ("source_layer", "humanbody:source_layer"), ("target_layer", "humanbody:target_layer")]:
                    if params.get(key) and params[key] not in {_tail(v) for v in _qvals(x, pid)}: break
                else:
                    if params.get("cross_layer") and x.get("assertion_id") not in cross_l: continue
                    if params.get("cross_scale") and x.get("assertion_id") not in cross_s: continue
                    if params.get("assertion_status") and x.get("assertion_status") != params["assertion_status"]: continue
                    if source_ids is not None and x.get("assertion_id") not in source_ids: continue
                    if evidence_ids is not None and x.get("assertion_id") not in evidence_ids: continue
                    if ontology_ids is not None and x.get("assertion_id") not in ontology_ids: continue
                    if params.get("mapped") and x.get("assertion_id") not in mapped_ids: continue
                    if params.get("text") and _norm(params["text"]) not in _norm(json.dumps(x, ensure_ascii=False)): continue
                    out.append(x)
                    if len(out) >= limit: break
            return AdapterResult(items=out, raw_item_count=len(out))
        if operation == "pathways":
            rows = self.read_json("corpus/pathways.json").get("pathways", [])
            if params.get("query"): rows = [x for x in rows if _norm(params["query"]) in _norm(json.dumps(x, ensure_ascii=False))]
        elif operation == "feedback_loops":
            rows = self.read_json("corpus/feedback-loops.json").get("loops", [])
            if params.get("query"): rows = [x for x in rows if _norm(params["query"]) in _norm(json.dumps(x, ensure_ascii=False))]
        elif operation == "glossary":
            rows = self.read_json("corpus/glossary.json").get("entries", [])
            if params.get("category"): rows = [x for x in rows if x.get("category") == params["category"]]
            if params.get("text"): rows = [x for x in rows if _norm(params["text"]) in _norm(json.dumps(x, ensure_ascii=False))]
        elif operation == "coverage": return AdapterResult(items=[self.read_json("corpus/coverage-report.json")])
        elif operation == "tensions": rows = self.read_json("corpus/tension-report.json").get("candidates", [])
        elif operation == "density": rows = [{"process": k, **v} for k, v in self.read_json("corpus/density-report.json").get("processes", {}).items()]
        elif operation == "depth": rows = [{"process": k, **v} for k, v in self.read_json("corpus/depth-report.json").get("processes", {}).items()]
        elif operation == "corroboration": rows = [{"process": k, **v} for k, v in self.read_json("corpus/corroboration-report.json").get("processes", {}).items()]
        elif operation == "coupling": rows = [{"process": k, **v} for k, v in self.read_json("corpus/process-coupling-report.json").get("processes", {}).items()]
        elif operation == "frontier": rows = self.read_json("corpus/enrichment-frontier.json").get("processes", [])
        else: raise AssertionError(operation)
        return AdapterResult(items=rows[:limit], raw_item_count=len(rows), truncated=len(rows) > limit)
