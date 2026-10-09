from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator

from kompiler.errors import AdmissionError
from kompiler.protocol.canonical import prefixed_hash
from kompiler.config import AppConfig
from kompiler.protocol.models import CapabilitySnapshot, QueryOperation, QueryPlan
from kompiler.registry import AdapterRegistry


@dataclass(slots=True)
class PlannedOperation:
    operation: QueryOperation
    dependencies: set[str]
    dependents: set[str]
    stage: int
    capability: Any


@dataclass(slots=True)
class ExecutionPlan:
    query: QueryPlan
    operations: dict[str, PlannedOperation]
    stages: list[list[str]]
    query_hash: str
    capability_snapshot_id: str


def _capability_map(snapshot: CapabilitySnapshot) -> dict[tuple[str, str], Any]:
    return {(t.target_id, op.operation_id): op for t in snapshot.targets for op in t.operations}


def build_plan(
    query: QueryPlan,
    registry: AdapterRegistry,
    *,
    config: AppConfig | None = None,
    allow_snapshot_drift: bool = False,
) -> ExecutionPlan:
    snapshot = registry.snapshot()
    if query.capability_snapshot_id and query.capability_snapshot_id != snapshot.snapshot_id:
        if not (allow_snapshot_drift or query.execution.allow_compatible_capability_drift):
            raise AdmissionError(
                "CAPABILITY_SNAPSHOT_MISMATCH",
                "Query capability snapshot does not match current runtime",
                {"requested": query.capability_snapshot_id, "current": snapshot.snapshot_id},
            )
    capmap = _capability_map(snapshot)
    ids = {op.id for op in query.operations}
    deps: dict[str, set[str]] = {}
    rev: dict[str, set[str]] = {x: set() for x in ids}
    for op in query.operations:
        key = (op.target, op.operation)
        cap = capmap.get(key)
        if cap is None:
            if op.target not in registry.targets:
                raise AdmissionError("UNKNOWN_TARGET", f"Unknown target {op.target}", {"available_targets": registry.targets}, op.id)
            available = [x.operation_id for x in next(t for t in snapshot.targets if t.target_id == op.target).operations]
            raise AdmissionError("UNKNOWN_OPERATION", f"Unknown operation {op.target}.{op.operation}", {"available_operations": available}, op.id)
        if not cap.semantics.read_only:
            raise AdmissionError("FORBIDDEN_OPERATION", f"Operation {op.target}.{op.operation} is not read-only", operation_id=op.id)
        if cap.semantics.requires_surface and op.surface is None:
            raise AdmissionError(
                "SURFACE_REQUIRED",
                f"Operation {op.target}.{op.operation} requires a v7 surface selector",
                {"required": ["subject.subject_id", "orientation.primary_axis"]},
                op.id,
            )
        if op.surface is not None and cap.semantics.semantic_plane != "meta":
            raise AdmissionError(
                "SURFACE_UNSUPPORTED",
                f"Operation {op.target}.{op.operation} does not consume a v7 surface selector",
                operation_id=op.id,
            )
        if cap.semantics.network and config is not None and config.network_default == "deny":
            raise AdmissionError(
                "NETWORK_DENIED",
                f"Operation {op.target}.{op.operation} requires network access but runtime policy denies it",
                operation_id=op.id,
            )
        validation_params = dict(op.params)
        for binding in op.inputs:
            if binding.inject_as and binding.inject_as not in validation_params:
                validation_params[binding.inject_as] = []
        errors = list(Draft202012Validator(cap.input_schema).iter_errors(validation_params))
        if errors:
            raise AdmissionError(
                "INVALID_PARAMETERS",
                f"Invalid parameters for {op.target}.{op.operation}",
                {"errors": [{"path": list(e.path), "message": e.message} for e in errors]},
                op.id,
            )
        from kompiler.planner.selector import select as _validate_selector
        for binding in op.inputs:
            _validate_selector({}, binding.selector)
        d = {b.from_operation for b in op.inputs}
        bad = sorted(d - ids)
        if bad:
            raise AdmissionError("INVALID_DEPENDENCY", f"Operation {op.id} references missing operations", {"missing": bad}, op.id)
        if op.id in d:
            raise AdmissionError("CYCLIC_PLAN", f"Operation {op.id} depends on itself", operation_id=op.id)
        deps[op.id] = d
        for parent in d: rev[parent].add(op.id)
    # Kahn topological stages.
    indeg = {k: len(v) for k, v in deps.items()}
    ready = sorted(k for k, n in indeg.items() if n == 0)
    stages: list[list[str]] = []
    stage_of: dict[str, int] = {}
    visited = 0
    while ready:
        stage = ready
        stages.append(stage)
        ready = []
        for node in stage:
            stage_of[node] = len(stages) - 1
            visited += 1
            for child in sorted(rev[node]):
                indeg[child] -= 1
                if indeg[child] == 0: ready.append(child)
        ready.sort()
    if visited != len(ids):
        cyclic = sorted(k for k, v in indeg.items() if v > 0)
        raise AdmissionError("CYCLIC_PLAN", "Query operation graph contains a cycle", {"operations": cyclic})
    # request_id is transport/audit identity, not query semantics. Cache preference and
    # scheduling parallelism likewise must not change the semantic query identity.
    qdump = query.model_dump(by_alias=True, mode="json", exclude_none=True)
    qdump.pop("request_id", None)
    # The optional retrieval profile is a backwards-compatible extension:
    # old requests implicitly used the balanced policy. Keep their query hash
    # stable while distinguishing explicit lexical queries.
    budget = qdump.get("budget")
    if isinstance(budget, dict) and budget.get("selection_mode") == "balanced":
        budget.pop("selection_mode", None)
    execution = qdump.get("execution")
    if isinstance(execution, dict):
        execution.pop("use_cache", None)
        execution.pop("max_parallelism", None)
    return ExecutionPlan(
        query=query,
        operations={op.id: PlannedOperation(op, deps[op.id], rev[op.id], stage_of[op.id], capmap[(op.target, op.operation)]) for op in query.operations},
        stages=stages,
        query_hash=prefixed_hash("qry", qdump),
        capability_snapshot_id=snapshot.snapshot_id,
    )
