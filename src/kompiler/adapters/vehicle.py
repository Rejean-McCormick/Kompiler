from __future__ import annotations

from typing import Any

from kompiler.adapters.base import AdapterContext, AdapterResult
from kompiler.protocol.models import OperationCapability

from .common import KristalAdapterBase, opcap
from .utils import run_python_json


KINDS = ["circuit", "component", "port", "connection", "path", "test", "failure", "state", "dependency", "component_archetype", "system_archetype", "symptom", "failure_archetype", "measurement", "safety_rule"]


class VehicleDiagAdapter(KristalAdapterBase):
    adapter_id = "kristal-vehiclediag"
    adapter_version = "1.0.0"
    target_id = "VehicleDiag"

    def __init__(self, root):
        super().__init__(root)
        self.schema_version = "2.0"
        self.identity_paths = [
            self.root / "manifest.sha256.json",
            self.root / "corpus/graph.json",
            self.root / "tools/query.py",
        ]

    def capabilities(self) -> list[OperationCapability]:
        return [opcap("get", "Return a vehicle diagnostic graph object by kind and ID.", {
            "kind": {"type": "string", "enum": KINDS}, "id": {"type": "string"}
        }, ["kind", "id"]), opcap("list", "List IDs for a vehicle diagnostic graph object kind.", {
            "kind": {"type": "string", "enum": KINDS}
        }, ["kind"], max_items=10000)]

    async def execute(self, operation: str, params: dict[str, Any], context: AdapterContext) -> AdapterResult:
        self.validate_params(operation, params)
        if operation == "get":
            return await run_python_json(self.root, self.root / "tools/query.py", [params["kind"], params["id"]], timeout_ms=context.timeout_ms, max_bytes=context.max_stdout_bytes)
        # Native list is line-oriented; direct-read for structural output.
        g = self.read_json("corpus/graph.json")
        kind = params["kind"]
        maps = {"circuit":"circuits_by_id","component":"components_by_id","port":"ports_by_id","connection":"connections_by_id","path":"paths_by_id","test":"test_points_by_id","failure":"failure_modes_by_id","state":"operating_states_by_id","dependency":"dependency_sets_by_id"}
        if kind in maps: ids = sorted(g[maps[kind]])
        else:
            catalogs = g["catalogs"]
            keymap = {"component_archetype":("component_archetypes","items"),"system_archetype":("system_archetypes","items"),"symptom":("symptom_ontology","nodes"),"failure_archetype":("failure_archetypes","items"),"measurement":("measurement_catalog","quantities"),"safety_rule":("safety_rules","rules")}
            a,b = keymap[kind]; ids = sorted(x["id"] for x in catalogs[a][b])
        limit = context.max_items or len(ids)
        return AdapterResult(items=[{"id": x, "kind": kind} for x in ids[:limit]], raw_item_count=len(ids), truncated=len(ids)>limit)
