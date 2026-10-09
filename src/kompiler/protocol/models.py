from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from kompiler.kristal_standard import standard_lock

SUPPORTED_KRISTAL_STANDARD_VERSION = str(standard_lock()["version"])

JsonValue = Any


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class LooseModel(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class RuntimeDescriptor(StrictModel):
    name: str = Field(default="kompiler", min_length=1)
    version: str = Field(min_length=1)
    standard_support: dict[str, list[str]] = Field(
        default_factory=lambda: {
            "kristal_state": ["6.0"],
            "kristall": ["7.0", "8.0"],
            "kristal_semantic_state": ["9.0"],
            "kristal_hosting": ["10.0"],
            "semantic_resonance": ["1.0"],
        }
    )
    conformance_profiles: dict[str, str] = Field(
        default_factory=lambda: {"kristal_v7": "V7-Projection", "kristal_v9": "V9-State-Reader", "kristal_v10": "V10-Publication-Reader"}
    )


class AdapterDescriptor(StrictModel):
    id: str = Field(min_length=1)
    version: str = Field(min_length=1)


class SourceDescriptor(LooseModel):
    kristal_schema_version: str | None = None
    state_id: str | None = None
    snapshot_id: str | None = None
    contract_family: str | None = None
    kristall_id: str | None = None
    namespace_id: str | None = None
    canonicalization_profile: str | None = None
    root_hint: str | None = None
    integrity: str | None = None


class OperationOutputDescriptor(StrictModel):
    record_kinds: list[str] = Field(default_factory=list)
    supports_provenance: bool = True


class OperationSemantics(StrictModel):
    read_only: bool = True
    deterministic: bool = True
    supports_reader_policy: bool = False
    network: bool = False
    semantic_plane: Literal["source", "meta"] = "source"
    requires_surface: bool = False
    v7_native: bool = False


class OperationLimits(StrictModel):
    max_items: int | None = None
    timeout_ms: int | None = None
    max_bytes: int | None = None


class OperationCapability(StrictModel):
    operation_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    input_schema: dict[str, Any] = Field(default_factory=lambda: {"type": "object"})
    output: OperationOutputDescriptor = Field(default_factory=OperationOutputDescriptor)
    semantics: OperationSemantics = Field(default_factory=OperationSemantics)
    limits: OperationLimits = Field(default_factory=OperationLimits)


class TargetCapability(StrictModel):
    target_id: str = Field(min_length=1)
    kind: str = "kristal"
    adapter: AdapterDescriptor
    source: SourceDescriptor = Field(default_factory=SourceDescriptor)
    operations: list[OperationCapability] = Field(default_factory=list)


class CapabilitySnapshot(StrictModel):
    protocol: Literal["kompiler.capabilities"] = "kompiler.capabilities"
    version: Literal["1.0", "1.1"] = "1.1"
    snapshot_id: str = Field(min_length=1)
    generated_at: datetime = Field(default_factory=utcnow)
    runtime: RuntimeDescriptor
    targets: list[TargetCapability]


class InputBinding(StrictModel):
    from_operation: str = Field(alias="from", min_length=1)
    selector: str = Field(default="$.records[*]", min_length=1)
    required: bool = True
    inject_as: str | None = None




class SurfaceSubject(StrictModel):
    subject_id: str = Field(min_length=1)


class SurfaceOrientation(StrictModel):
    primary_axis: str = Field(min_length=1)
    secondary_axis: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def distinct_axes(self) -> "SurfaceOrientation":
        if self.secondary_axis and self.secondary_axis == self.primary_axis:
            raise ValueError("secondary orientation axis must differ from primary axis")
        return self


class SurfaceSelector(StrictModel):
    subject: SurfaceSubject
    orientation: SurfaceOrientation
    context: dict[str, Any] = Field(default_factory=dict)
    source_policy: dict[str, Any] = Field(default_factory=dict)
    conflict_policy: Literal["preserve_disagreement"] = "preserve_disagreement"

class OperationBudget(StrictModel):
    max_items: int | None = Field(default=None, ge=1)
    max_bytes: int | None = Field(default=None, ge=1)


ErrorPolicy = Literal["abort_run", "fail_dependents", "continue"]


class QueryOperation(StrictModel):
    id: str = Field(min_length=1)
    target: str = Field(min_length=1)
    operation: str = Field(min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)
    surface: SurfaceSelector | None = None
    inputs: list[InputBinding] = Field(default_factory=list)
    budget: OperationBudget | None = None
    timeout_ms: int | None = Field(default=None, ge=1)
    on_error: ErrorPolicy | None = None


class QueryContext(StrictModel):
    reader_policy: str | None = None
    locale: str | None = "fr-CA"


class QueryBudget(StrictModel):
    max_items: int | None = Field(default=1200, ge=1)
    max_bytes: int | None = Field(default=1_500_000, ge=1)
    target_tokens: int | None = Field(default=120_000, ge=1)
    selection_mode: Literal["balanced", "lexical"] = "balanced"


class ExecutionOptions(StrictModel):
    max_parallelism: int = Field(default=4, ge=1)
    default_timeout_ms: int = Field(default=30_000, ge=1)
    on_operation_error: ErrorPolicy = "fail_dependents"
    allow_compatible_capability_drift: bool = False
    use_cache: bool = True


class ReturnOptions(StrictModel):
    include_provenance: bool = True
    include_raw_refs: bool = True
    include_conflicts: bool = True
    include_gaps: bool = True
    include_operation_outputs: bool = False


class QueryPlan(StrictModel):
    protocol: Literal["kompiler.query"] = "kompiler.query"
    version: Literal["1.0", "1.1"] = "1.1"
    request_id: str = Field(min_length=1)
    capability_snapshot_id: str | None = None
    intent: str | None = None
    topic: str | None = None
    parent_context_pack_id: str | None = None
    operations: list[QueryOperation] = Field(min_length=1)
    context: QueryContext = Field(default_factory=QueryContext)
    budget: QueryBudget = Field(default_factory=QueryBudget)
    execution: ExecutionOptions = Field(default_factory=ExecutionOptions)
    return_: ReturnOptions = Field(default_factory=ReturnOptions, alias="return")

    @model_validator(mode="after")
    def unique_operation_ids(self) -> "QueryPlan":
        ids = [op.id for op in self.operations]
        if len(ids) != len(set(ids)):
            raise ValueError("operation IDs must be unique")
        return self


class Statement(LooseModel):
    subject: Any = None
    predicate: Any = None
    object: Any = None


class Epistemics(LooseModel):
    assertion_status: str | None = None
    valuations: list[Any] = Field(default_factory=list)
    certainty_level_legacy: str | None = None
    validation: Any = None
    authority_recognition: Any = None
    record_role: str | None = None
    actionability: Any = None


class NormalizedRecord(LooseModel):
    record_id: str
    kind: str = "record"
    semantic_id: str | None = None
    semantic_role: Literal["source_assertion", "derived_assertion", "structural_relation", "similarity_signal", "hypothesis", "path", "entity", "record"] = "record"
    target_id: str | None = None
    operation_id: str | None = None
    referent_ids: list[str] = Field(default_factory=list)
    statement: Statement | dict[str, Any] | None = None
    content: Any = None
    epistemics: Epistemics = Field(default_factory=Epistemics)
    coordinates: dict[str, Any] = Field(default_factory=dict)
    applicability: dict[str, Any] = Field(default_factory=dict)
    provenance_refs: list[str] = Field(default_factory=list)
    source_record_ref: str | None = None
    raw_ref: str | None = None


class Referent(LooseModel):
    referent_id: str
    label: str | None = None
    kind: str | None = None
    external_ids: list[Any] = Field(default_factory=list)
    provenance_refs: list[str] = Field(default_factory=list)


class NormalizedRelation(LooseModel):
    relation_id: str
    subject_ref: str
    predicate: str
    object_ref: str
    record_ref: str | None = None
    edge_semantics: str | None = None
    status: str | None = None
    source_assertion_refs: list[dict[str, Any]] = Field(default_factory=list)
    derivation_record_id: str | None = None
    resonance_refs: list[str] = Field(default_factory=list)
    provenance_refs: list[str] = Field(default_factory=list)




class SubjectRegionItem(LooseModel):
    subject_id: str
    label: str | None = None
    description: str | None = None
    selector_ref: str | None = None


class OrientationAxisItem(LooseModel):
    axis_id: str
    label: str | None = None
    description: str | None = None
    status: str | None = None
    semantics: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)


class AssertionFamilyItem(LooseModel):
    family_id: str
    family_type: str
    status: str | None = None
    members: list[dict[str, Any]] = Field(default_factory=list)
    representative: dict[str, Any] | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)


class ResonanceObservation(LooseModel):
    resonance_id: str
    left: dict[str, Any]
    right: dict[str, Any]
    directionality: str
    dimensions: list[dict[str, Any]] = Field(default_factory=list)
    aggregate: dict[str, Any] | None = None
    status: str
    context: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)


class SurfaceDescriptor(LooseModel):
    surface_id: str
    kristall_id: str | None = None
    namespace_id: str | None = None
    subject: SurfaceSubject
    orientation: SurfaceOrientation
    context: dict[str, Any] = Field(default_factory=dict)
    source_policy: dict[str, Any] = Field(default_factory=dict)
    conflict_policy: str = "preserve_disagreement"
    snapshot_id: str | None = None
    selection: dict[str, Any] = Field(default_factory=dict)

class DerivedItem(LooseModel):
    derived_id: str
    kind: str
    value: Any
    transform: str
    input_refs: list[str] = Field(default_factory=list)


class ConflictItem(LooseModel):
    conflict_id: str
    record_refs: list[str]
    basis: str
    resolution: str = "unresolved"


class GapItem(LooseModel):
    gap_id: str
    question: str
    basis: str | None = None
    operation_id: str | None = None


class SourceItem(LooseModel):
    source_id: str
    title: str | None = None
    url: str | None = None
    target_id: str | None = None
    source_state_id: str | None = None


class OperationReceipt(LooseModel):
    operation_id: str
    status: Literal["pending", "running", "success", "failed", "skipped", "cancelled"]
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = None
    adapter_id: str | None = None
    adapter_version: str | None = None
    source_state_id: str | None = None
    source_snapshot_id: str | None = None
    source_contract_family: str | None = None
    kristall_id: str | None = None
    raw_item_count: int = 0
    normalized_item_count: int = 0
    truncated: bool = False
    cache_hit: bool = False
    error_code: str | None = None
    error_message: str | None = None


class ExecutionSummary(LooseModel):
    run_id: str
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: int | None = None
    receipts: list[OperationReceipt] = Field(default_factory=list)
    config_hash: str | None = None
    query_hash: str | None = None
    cache_hits: int = 0


class ContextSummary(LooseModel):
    record_count: int = 0
    referent_count: int = 0
    relation_count: int = 0
    subject_count: int = 0
    axis_count: int = 0
    assertion_family_count: int = 0
    resonance_count: int = 0
    surface_count: int = 0
    conflict_count: int = 0
    gap_count: int = 0
    derived_count: int = 0
    source_count: int = 0
    targets: list[str] = Field(default_factory=list)
    truncated: bool = False


class ContextPack(StrictModel):
    protocol: Literal["kompiler.context-pack"] = "kompiler.context-pack"
    version: Literal["1.0", "1.1"] = "1.1"
    context_pack_id: str
    semantic_hash: str
    artifact_hash: str | None = None
    request_id: str
    parent_context_pack_id: str | None = None
    generated_at: datetime = Field(default_factory=utcnow)
    status: Literal["success", "partial", "empty"] = "success"
    topic: str | None = None
    summary: ContextSummary = Field(default_factory=ContextSummary)
    referents: list[Referent] = Field(default_factory=list)
    records: list[NormalizedRecord] = Field(default_factory=list)
    relations: list[NormalizedRelation] = Field(default_factory=list)
    subjects: list[SubjectRegionItem] = Field(default_factory=list)
    axes: list[OrientationAxisItem] = Field(default_factory=list)
    assertion_families: list[AssertionFamilyItem] = Field(default_factory=list)
    resonance: list[ResonanceObservation] = Field(default_factory=list)
    surfaces: list[SurfaceDescriptor] = Field(default_factory=list)
    derived: list[DerivedItem] = Field(default_factory=list)
    conflicts: list[ConflictItem] = Field(default_factory=list)
    gaps: list[GapItem] = Field(default_factory=list)
    sources: list[SourceItem] = Field(default_factory=list)
    execution: ExecutionSummary
    provenance: dict[str, Any] = Field(default_factory=dict)
    operation_outputs: dict[str, Any] | None = None


class ErrorBody(StrictModel):
    code: str
    message: str
    operation_id: str | None = None
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorArtifact(StrictModel):
    protocol: Literal["kompiler.error"] = "kompiler.error"
    version: Literal["1.0", "1.1"] = "1.1"
    request_id: str | None = None
    generated_at: datetime = Field(default_factory=utcnow)
    error: ErrorBody
