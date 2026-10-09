from __future__ import annotations

import json
from typing import Any

from kompiler.adapters.base import AdapterContext, AdapterResult
from kompiler.protocol.models import OperationCapability

from .common import KristalAdapterBase, infer_schema_version, opcap


class PowerAdapter(KristalAdapterBase):
    adapter_id = "kristal-power"
    adapter_version = "1.0.0"
    target_id = "Power"

    def __init__(self, root):
        super().__init__(root)
        state = self.root / "corpus/power-topology.structured-epistemic-state.json"
        self.schema_version = infer_schema_version(state)
        self.identity_paths = [
            state,
            self.root / "sources/lexicon/labels.fr.json",
            self.root / "sources/lexicon/aliases.fr.json",
            self.root / "sources/ontology/concepts.json",
            self.root / "sources/epistemology/definitions.editorial.fr.json",
            self.root / "sources/epistemology/definitions.sourced.fr.json",
            self.root / "sources/graph/taxonomy.json",
            self.root / "sources/graph/semantic_relations.json",
            self.root / "sources/power_dynamics/definitions.json",
            self.root / "sources/power_dynamics/dynamic_relations.json",
            self.root / "sources/power_dynamics/source_glossary.json",
            self.root / "sources/power_dynamics/document_catalog.json",
            self.root / "sources/power_dynamics/case_profiles.json",
            self.root / "sources/power_dynamics/schema_registry.json",
            self.root / "sources/theories/positions.json",
        ]

    def capabilities(self) -> list[OperationCapability]:
        s = {"type": "string"}
        return [
            opcap("search", "Search power concepts, sourced definitions, dynamics, source terms, documents and cases.", {"text": s, "limit": {"type": "integer", "minimum": 1, "maximum": 5000}}, ["text"]),
            opcap("concept", "Return one concept and its labels/definitions/relations.", {"concept_id": s}, ["concept_id"]),
            opcap("relations", "Return graph relations touching a concept.", {"concept_id": s}, ["concept_id"], record_kinds=["relation"]),
            opcap("cases", "Search Power Dynamics case profiles.", {"text": s, "limit": {"type": "integer", "minimum": 1, "maximum": 1000}}),
            opcap("schemas", "Search Power Dynamics schema registry.", {"text": s, "limit": {"type": "integer", "minimum": 1, "maximum": 1000}}),
            opcap("assertions", "Search structured epistemic assertions by free text.", {"text": s, "limit": {"type": "integer", "minimum": 1, "maximum": 5000}}, record_kinds=["assertion", "relation"]),
        ]

    def _graph(self):
        labels = self.read_json("sources/lexicon/labels.fr.json").get("labels", [])
        aliases = self.read_json("sources/lexicon/aliases.fr.json").get("aliases", [])
        concepts = self.read_json("sources/ontology/concepts.json").get("concepts", [])
        defs = self.read_json("sources/epistemology/definitions.editorial.fr.json").get("definitions", [])
        sdefs = self.read_json("sources/epistemology/definitions.sourced.fr.json").get("definitions", [])
        pddefs = self.read_json("sources/power_dynamics/definitions.json").get("definitions", [])
        rels = []
        for rel, key in [("sources/graph/taxonomy.json", "edges"), ("sources/graph/semantic_relations.json", "edges"), ("sources/power_dynamics/dynamic_relations.json", "edges"), ("sources/theories/positions.json", "positions")]:
            rels += self.read_json(rel).get(key, [])
        return labels, aliases, concepts, defs, sdefs, pddefs, rels

    async def execute(self, operation: str, params: dict[str, Any], context: AdapterContext) -> AdapterResult:
        self.validate_params(operation, params)
        limit = min(int(params.get("limit", context.max_items or 1000)), context.max_items or 5000)
        if operation in {"search", "concept", "relations"}:
            labels, aliases, concepts, defs, sdefs, pddefs, rels = self._graph()
            label_map = {x["concept_ref"]: x.get("preferred_label") for x in labels}
            concept_map = {x["id"]: x for x in concepts}
            alias_map: dict[str, list[str]] = {}
            for a in aliases: alias_map.setdefault(a["concept_ref"], []).append(a.get("alias", ""))
            def_map = {x["concept_ref"]: x.get("text", "") for x in defs}
            sourced: dict[str, list[dict[str, Any]]] = {}
            for x in sdefs: sourced.setdefault(x["concept_ref"], []).append(x)
            pd: dict[str, list[dict[str, Any]]] = {}
            for x in pddefs: pd.setdefault(x["concept_ref"], []).append(x)
            if operation == "concept": ids = [params["concept_id"]] if params["concept_id"] in concept_map else []
            elif operation == "relations":
                cid = params["concept_id"]
                rows = [x for x in rels if x.get("subject_ref") == cid or x.get("object_ref") == cid]
                return AdapterResult(items=rows[:limit], raw_item_count=len(rows), truncated=len(rows) > limit)
            else:
                q = params["text"].lower(); ids = []
                for cid, concept in concept_map.items():
                    hay = " ".join([cid, label_map.get(cid, ""), def_map.get(cid, ""), *alias_map.get(cid, []), *[d.get("text", "") for d in sourced.get(cid, [])], *[d.get("text", "") for d in pd.get(cid, [])]]).lower()
                    if q in hay: ids.append(cid)
            rows = []
            for cid in ids[:limit]:
                rows.append({"id": cid, "label": label_map.get(cid), "concept": concept_map[cid], "editorial_definition": def_map.get(cid), "sourced_definitions": sourced.get(cid, []), "power_dynamics_definitions": pd.get(cid, []), "relations": [x for x in rels if x.get("subject_ref") == cid or x.get("object_ref") == cid]})
            if operation == "search":
                q = params["text"].lower()
                terms = [x for x in self.read_json("sources/power_dynamics/source_glossary.json").get("terms", []) if q in (x.get("term", "") + " " + x.get("definition", "")).lower()]
                docs = [x for x in self.read_json("sources/power_dynamics/document_catalog.json").get("documents", []) if q in json.dumps(x, ensure_ascii=False).lower()]
                cases = [x for x in self.read_json("sources/power_dynamics/case_profiles.json").get("cases", []) if q in json.dumps(x, ensure_ascii=False).lower()]
                rows += [{"kind": "source_term", **x} for x in terms] + [{"kind": "document", **x} for x in docs] + [{"kind": "case", **x} for x in cases]
            return AdapterResult(items=rows[:limit], raw_item_count=len(rows), truncated=len(rows) > limit)
        if operation == "cases":
            rows = self.read_json("sources/power_dynamics/case_profiles.json").get("cases", [])
        elif operation == "schemas": rows = self.read_json("sources/power_dynamics/schema_registry.json").get("schemas", [])
        elif operation == "assertions": rows = self.read_json("corpus/power-topology.structured-epistemic-state.json").get("assertions", [])
        else: raise AssertionError(operation)
        if params.get("text"): rows = [x for x in rows if params["text"].lower() in json.dumps(x, ensure_ascii=False).lower()]
        return AdapterResult(items=rows[:limit], raw_item_count=len(rows), truncated=len(rows) > limit)
