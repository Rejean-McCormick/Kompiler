from __future__ import annotations

from typing import Any

from kompiler.adapters.base import AdapterContext, AdapterResult
from kompiler.protocol.models import OperationCapability

from .common import KristalAdapterBase, opcap
from .utils import run_python_json


class RecipesAdapter(KristalAdapterBase):
    adapter_id = "kristal-recipes"
    adapter_version = "1.0.0"
    target_id = "Recipes"

    def __init__(self, root):
        super().__init__(root)
        self.schema_version = "2.1"
        self.identity_paths = [
            self.root / "manifest.sha256.json",
            self.root / "corpus/index.json",
            self.root / "tools/query.py",
        ]

    def capabilities(self) -> list[OperationCapability]:
        s = {"type": "string"}
        n = {"type": "number", "minimum": 0}
        return [
            opcap("stats", "Return recipe corpus statistics.", {}),
            opcap("family", "Return variants and variation space for a recipe family.", {"family": s}, ["family"]),
            opcap("ingredient", "Return variants indexed by ingredient.", {"ingredient": s}, ["ingredient"]),
            opcap("technique", "Return variants indexed by technique.", {"technique": s}, ["technique"]),
            opcap("role", "Return variants indexed by ingredient role.", {"role": s}, ["role"]),
            opcap("mechanism", "Return variants indexed by mechanism.", {"mechanism": s}, ["mechanism"]),
            opcap("state", "Return variants indexed by state.", {"state": s}, ["state"]),
            opcap("sensory", "Return variants indexed by sensory dimension/slug.", {"sensory": s}, ["sensory"]),
            opcap("facet", "Return variants indexed by facet dimension/slug.", {"facet": s}, ["facet"]),
            opcap("similar", "Return likely duplicate/similar variants.", {"variant": s, "limit": {"type": "integer", "minimum": 1, "maximum": 1000}}, ["variant"]),
            opcap("substitutions", "Return substitution rules touching an ingredient.", {"ingredient": s}, ["ingredient"]),
            opcap("troubleshoot", "Return failure modes for a recipe family.", {"family": s}, ["family"]),
            opcap("preparations", "Return preparation observations for a variant.", {"variant": s}, ["variant"]),
            opcap("search", "Filter recipe search documents across ingredients, techniques, roles, mechanisms, states, equipment, facets and timing.", {
                "ingredients": {"type": "array", "items": s}, "exclude_ingredients": {"type": "array", "items": s},
                "techniques": {"type": "array", "items": s}, "roles": {"type": "array", "items": s},
                "mechanisms": {"type": "array", "items": s}, "states": {"type": "array", "items": s},
                "equipment": {"type": "array", "items": s}, "facets": {"type": "array", "items": s},
                "max_critical_min": n, "max_active_min": n, "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
            }, max_items=1000),
        ]

    async def execute(self, operation: str, params: dict[str, Any], context: AdapterContext) -> AdapterResult:
        self.validate_params(operation, params)
        args: list[str] = []
        if operation == "stats": args = ["--stats"]
        elif operation in {"family", "ingredient", "technique", "role", "mechanism", "state", "sensory", "facet"}: args = [f"--{operation}", str(params[operation])]
        elif operation == "similar": args = ["--similar", str(params["variant"])]
        elif operation == "substitutions": args = ["--substitutions", str(params["ingredient"])]
        elif operation == "troubleshoot": args = ["--troubleshoot", str(params["family"])]
        elif operation == "preparations": args = ["--preparations", str(params["variant"])]
        elif operation == "search":
            for key in ["ingredients", "exclude_ingredients", "techniques", "roles", "mechanisms", "states", "equipment", "facets"]:
                if params.get(key): args += ["--" + key.replace("_", "-"), ",".join(str(x) for x in params[key])]
            if params.get("max_critical_min") is not None: args += ["--max-critical-min", str(params["max_critical_min"])]
            if params.get("max_active_min") is not None: args += ["--max-active-min", str(params["max_active_min"])]
        else: raise AssertionError(operation)
        if operation in {"similar", "search"}: args += ["--limit", str(min(int(params.get("limit", context.max_items or 20)), context.max_items or 1000))]
        return await run_python_json(self.root, self.root / "tools/query.py", args, timeout_ms=context.timeout_ms, max_bytes=context.max_stdout_bytes)
