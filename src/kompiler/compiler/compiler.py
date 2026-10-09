from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from kompiler.budgeting import select_records
from kompiler.errors import CompilationError
from kompiler.normalization import NormalizedBatch
from kompiler.protocol.canonical import canonical_bytes, prefixed_hash
from kompiler.protocol.models import (
    AssertionFamilyItem,
    ConflictItem,
    ContextPack,
    ContextSummary,
    DerivedItem,
    ExecutionSummary,
    GapItem,
    OrientationAxisItem,
    QueryBudget,
    QueryPlan,
    ResonanceObservation,
    SubjectRegionItem,
    SurfaceDescriptor,
)


def _record_key(record) -> tuple[str, str] | None:
    st = record.statement
    if not st:
        return None
    d = st.model_dump(mode="json", exclude_none=True) if hasattr(st, "model_dump") else st
    s, p = d.get("subject"), d.get("predicate")
    if isinstance(s, dict):
        stable = s.get("external_id") or s.get("id")
        s = f"id:{stable}" if stable is not None else f"target:{record.target_id}:label:{s.get('label')}"
    if isinstance(p, dict):
        stable = p.get("external_id") or p.get("id")
        p = f"id:{stable}" if stable is not None else f"target:{record.target_id}:label:{p.get('label')}"
    if s is None or p is None:
        return None
    return str(s), str(p)


def _object_value(record) -> Any:
    st = record.statement
    if not st:
        return None
    d = st.model_dump(mode="json", exclude_none=True) if hasattr(st, "model_dump") else st
    o = d.get("object")
    return o.get("value") if isinstance(o, dict) and "value" in o else o


def _semantic_execution(execution: ExecutionSummary) -> dict[str, Any]:
    """Keep only execution facts that can affect the resulting knowledge artifact."""
    receipts = []
    for receipt in execution.receipts:
        receipts.append(
            {
                "operation_id": receipt.operation_id,
                "status": receipt.status,
                "adapter_id": receipt.adapter_id,
                "adapter_version": receipt.adapter_version,
                "source_state_id": receipt.source_state_id,
                "source_snapshot_id": receipt.source_snapshot_id,
                "source_contract_family": receipt.source_contract_family,
                "kristall_id": receipt.kristall_id,
                "raw_item_count": receipt.raw_item_count,
                "normalized_item_count": receipt.normalized_item_count,
                "truncated": receipt.truncated,
                "error_code": receipt.error_code,
            }
        )
    return {
        "receipts": receipts,
        "config_hash": execution.config_hash,
        "query_hash": execution.query_hash,
    }


def _effective_max_bytes(budget: QueryBudget) -> int:
    value = budget.max_bytes or 2**63 - 1
    if budget.target_tokens:
        value = min(value, budget.target_tokens * 4)
    return value


def _canonical_pack_size(pack: ContextPack) -> int:
    data = pack.model_dump(by_alias=True, mode="json", exclude_none=True)
    # Reserve the exact-length artifact hash field before it has been calculated.
    data["artifact_hash"] = "artifact:sha256:" + ("0" * 64)
    return len(canonical_bytes(data))


def compile_context_pack(
    query: QueryPlan,
    batches: dict[str, NormalizedBatch],
    execution: ExecutionSummary,
    *,
    provenance: dict[str, Any],
    operation_outputs: dict[str, Any] | None = None,
    effective_budget: QueryBudget | None = None,
) -> ContextPack:
    budget = effective_budget or query.budget
    records = []
    refs = {}
    rels = {}
    sources = {}
    subjects: dict[str, SubjectRegionItem] = {}
    axes: dict[str, OrientationAxisItem] = {}
    families: dict[str, AssertionFamilyItem] = {}
    resonance: dict[str, ResonanceObservation] = {}
    surfaces: dict[str, SurfaceDescriptor] = {}
    adapter_derived: list[DerivedItem] = []
    for op_id in sorted(batches):
        batch = batches[op_id]
        records.extend(batch.records)
        for item in batch.referents:
            refs.setdefault(item.referent_id, item)
        for item in batch.relations:
            rels.setdefault(item.relation_id, item)
        for item in batch.sources:
            sources.setdefault(item.source_id, item)
        for item in batch.subjects:
            subjects.setdefault(item.subject_id, item)
        for item in batch.axes:
            axes.setdefault(item.axis_id, item)
        for item in batch.assertion_families:
            families.setdefault(item.family_id, item)
        for item in batch.resonance:
            resonance.setdefault(item.resonance_id, item)
        for item in batch.surfaces:
            surfaces.setdefault(item.surface_id, item)
        for item in batch.derived:
            adapter_derived.append(
                DerivedItem.model_validate(item)
                if "derived_id" in item
                else DerivedItem(
                    derived_id=prefixed_hash("drv", item),
                    kind="adapter",
                    value=item,
                    transform="adapter/1.0",
                )
            )

    # Exact dedupe by record identity, preserving deterministic first occurrence.
    uniq = {}
    for record in sorted(records, key=lambda x: (x.target_id or "", x.operation_id or "", x.record_id)):
        uniq.setdefault(record.record_id, record)
    records = list(uniq.values())
    initially_selected, record_budget_truncated = select_records(records, budget, topic=query.topic or "")
    # Avoid mutating normalized batches when return options strip fields.
    initially_selected = [r.model_copy(deep=True) for r in initially_selected]
    if not query.return_.include_raw_refs:
        for record in initially_selected:
            record.raw_ref = None

    receipt_by_id = {r.operation_id: r for r in execution.receipts}
    base_gaps: list[GapItem] = []
    for op in query.operations:
        receipt = receipt_by_id.get(op.id)
        if receipt is None or receipt.status in {"failed", "skipped", "cancelled"}:
            base_gaps.append(
                GapItem(
                    gap_id=prefixed_hash(
                        "gap", {"op": op.id, "status": receipt.status if receipt else "missing"}
                    ),
                    question=f"Operation {op.id} did not produce usable context.",
                    basis=receipt.error_code if receipt else "missing_receipt",
                    operation_id=op.id,
                )
            )
        elif receipt.normalized_item_count == 0:
            base_gaps.append(
                GapItem(
                    gap_id=prefixed_hash("gap", {"op": op.id, "status": "zero"}),
                    question=f"Operation {op.id} returned no records.",
                    basis="zero_records",
                    operation_id=op.id,
                )
            )

    max_bytes = _effective_max_bytes(budget)
    outputs = operation_outputs if query.return_.include_operation_outputs else None
    output_budget_truncated = False

    def assemble(selected, *, outputs_value, adapter_derived_value, force_budget_gap: bool) -> ContextPack:
        selected_ids = {r.record_id for r in selected}
        rel_list = [
            item for item in rels.values() if item.record_ref is None or item.record_ref in selected_ids
        ]

        used_referents = {rid for record in selected for rid in record.referent_ids}
        for rel in rel_list:
            used_referents.add(rel.subject_ref)
            used_referents.add(rel.object_ref)
        referent_list = sorted(
            (item for key, item in refs.items() if key in used_referents), key=lambda x: x.referent_id
        )

        used_sources = {ref for record in selected for ref in record.provenance_refs}
        source_list = sorted(
            (item for key, item in sources.items() if key in used_sources), key=lambda x: x.source_id
        )
        # A v7 Surface adapter has already applied source_policy. Preserve those declared
        # source records even when no selected assertion carries a direct provenance_ref.
        if surfaces:
            source_list = sorted(sources.values(), key=lambda x: x.source_id)
        # v7 meta-objects are already surface-scoped by adapters. They remain separate
        # from factual records so no semantic promotion occurs during compilation.
        subject_list = sorted(subjects.values(), key=lambda x: x.subject_id)
        axis_list = sorted(axes.values(), key=lambda x: x.axis_id)
        family_list = sorted(families.values(), key=lambda x: x.family_id)
        resonance_list = sorted(resonance.values(), key=lambda x: x.resonance_id)
        surface_list = sorted(surfaces.values(), key=lambda x: x.surface_id)

        conflicts: list[ConflictItem] = []
        groups = defaultdict(list)
        for record in selected:
            key = _record_key(record)
            if key:
                groups[key].append(record)
        for key, rows in sorted(groups.items()):
            vals = {prefixed_hash("obj", _object_value(r)) for r in rows}
            if len(vals) > 1:
                conflicts.append(
                    ConflictItem(
                        conflict_id=prefixed_hash(
                            "conf", {"key": key, "records": [r.record_id for r in rows]}
                        ),
                        record_refs=[r.record_id for r in rows],
                        basis="incompatible_values",
                    )
                )

        valid_adapter_derived = [
            item
            for item in adapter_derived_value
            if not item.input_refs or all(ref in selected_ids for ref in item.input_refs)
        ]
        item_limit = budget.max_items or 2**63 - 1
        derived_room = max(0, item_limit - len(selected))
        derived = valid_adapter_derived[:derived_room]
        derived_item_truncated = len(derived) < len(valid_adapter_derived)
        coverage = defaultdict(int)
        for record in selected:
            coverage[record.target_id or "unknown"] += 1
        if coverage and len(selected) + len(derived) < item_limit:
            derived.append(
                DerivedItem(
                    derived_id=prefixed_hash("drv", dict(sorted(coverage.items()))),
                    kind="coverage",
                    value=dict(sorted(coverage.items())),
                    transform="coverage_by_target/1.0",
                    input_refs=[r.record_id for r in selected],
                )
            )

        gaps = list(base_gaps)
        is_truncated = (
            record_budget_truncated
            or force_budget_gap
            or derived_item_truncated
            or any(receipt.truncated for receipt in execution.receipts)
        )
        if is_truncated:
            gaps.append(
                GapItem(
                    gap_id=prefixed_hash("gap", {"query": execution.query_hash, "budget": "truncated"}),
                    question="Some context was omitted by operation or Context Pack budgets.",
                    basis="context_budget",
                )
            )

        summary = ContextSummary(
            record_count=len(selected),
            referent_count=len(referent_list),
            relation_count=len(rel_list),
            subject_count=len(subject_list),
            axis_count=len(axis_list),
            assertion_family_count=len(family_list),
            resonance_count=len(resonance_list),
            surface_count=len(surface_list),
            conflict_count=len(conflicts) if query.return_.include_conflicts else 0,
            gap_count=len(gaps) if query.return_.include_gaps else 0,
            derived_count=len(derived),
            source_count=len(source_list),
            targets=sorted({r.target_id for r in selected if r.target_id}),
            truncated=is_truncated,
        )

        failed = any(r.status != "success" for r in execution.receipts)
        status = "partial" if failed or is_truncated else ("empty" if not selected else "success")
        visible_conflicts = conflicts if query.return_.include_conflicts else []
        visible_gaps = gaps if query.return_.include_gaps else []
        visible_provenance = provenance if query.return_.include_provenance else {}

        semantic_body = {
            "protocol": "kompiler.context-pack",
            "version": "1.1",
            "parent_context_pack_id": query.parent_context_pack_id,
            "status": status,
            "topic": query.topic,
            "summary": summary.model_dump(mode="json"),
            "referents": [x.model_dump(mode="json", exclude_none=True) for x in referent_list],
            "records": [x.model_dump(mode="json", exclude_none=True) for x in selected],
            "relations": [x.model_dump(mode="json", exclude_none=True) for x in sorted(rel_list, key=lambda x: x.relation_id)],
            "subjects": [x.model_dump(mode="json", exclude_none=True) for x in subject_list],
            "axes": [x.model_dump(mode="json", exclude_none=True) for x in axis_list],
            "assertion_families": [x.model_dump(mode="json", exclude_none=True) for x in family_list],
            "resonance": [x.model_dump(mode="json", exclude_none=True) for x in resonance_list],
            "surfaces": [x.model_dump(mode="json", exclude_none=True) for x in surface_list],
            "derived": [x.model_dump(mode="json", exclude_none=True) for x in derived],
            "conflicts": [x.model_dump(mode="json", exclude_none=True) for x in visible_conflicts],
            "gaps": [x.model_dump(mode="json", exclude_none=True) for x in visible_gaps],
            "sources": [x.model_dump(mode="json", exclude_none=True) for x in source_list],
            "execution": _semantic_execution(execution),
            "provenance": visible_provenance,
            "operation_outputs": outputs_value,
        }
        semantic_hash = prefixed_hash("ctx", semantic_body)
        return ContextPack(
            context_pack_id=semantic_hash,
            semantic_hash=semantic_hash,
            request_id=query.request_id,
            parent_context_pack_id=query.parent_context_pack_id,
            generated_at=datetime.now(timezone.utc),
            status=status,
            topic=query.topic,
            summary=summary,
            referents=referent_list,
            records=list(selected),
            relations=sorted(rel_list, key=lambda x: x.relation_id),
            subjects=subject_list,
            axes=axis_list,
            assertion_families=family_list,
            resonance=resonance_list,
            surfaces=surface_list,
            derived=derived,
            conflicts=visible_conflicts,
            gaps=visible_gaps,
            sources=source_list,
            execution=execution,
            provenance=visible_provenance,
            operation_outputs=outputs_value,
        )

    # First, operation outputs are optional diagnostic payload. They are dropped before
    # sacrificing core normalized context when a total byte budget is exceeded.
    selected = initially_selected
    derived_value = adapter_derived
    pack = assemble(selected, outputs_value=outputs, adapter_derived_value=derived_value, force_budget_gap=False)
    if _canonical_pack_size(pack) > max_bytes and outputs is not None:
        outputs = None
        output_budget_truncated = True
        pack = assemble(selected, outputs_value=None, adapter_derived_value=derived_value, force_budget_gap=True)

    # Binary-search the largest deterministic record prefix that fits the complete artifact.
    if _canonical_pack_size(pack) > max_bytes and selected:
        original = selected
        lo, hi = 0, len(original)
        best = None
        while lo <= hi:
            mid = (lo + hi) // 2
            candidate = assemble(
                original[:mid],
                outputs_value=outputs,
                adapter_derived_value=derived_value,
                force_budget_gap=True,
            )
            if _canonical_pack_size(candidate) <= max_bytes:
                best = candidate
                lo = mid + 1
            else:
                hi = mid - 1
        if best is not None:
            pack = best
            selected = list(best.records)
        else:
            selected = []
            pack = assemble([], outputs_value=outputs, adapter_derived_value=derived_value, force_budget_gap=True)

    # Adapter-derived diagnostic content can itself be large. Trim it only after records.
    if _canonical_pack_size(pack) > max_bytes and derived_value:
        lo, hi = 0, len(derived_value)
        best = None
        while lo <= hi:
            mid = (lo + hi) // 2
            candidate = assemble(
                selected,
                outputs_value=outputs,
                adapter_derived_value=derived_value[:mid],
                force_budget_gap=True,
            )
            if _canonical_pack_size(candidate) <= max_bytes:
                best = candidate
                lo = mid + 1
            else:
                hi = mid - 1
        if best is not None:
            pack = best
        else:
            pack = assemble(selected, outputs_value=outputs, adapter_derived_value=[], force_budget_gap=True)

    if _canonical_pack_size(pack) > max_bytes:
        raise CompilationError(
            "BUDGET_IMPOSSIBLE",
            "Context Pack fixed metadata exceeds the requested byte budget",
            {"max_bytes": max_bytes, "minimum_observed_bytes": _canonical_pack_size(pack)},
        )

    if output_budget_truncated and not pack.summary.truncated:
        # Defensive; assemble(force_budget_gap=True) normally makes this true.
        pack.summary.truncated = True

    artifact = pack.model_dump(by_alias=True, mode="json", exclude_none=True)
    artifact.pop("artifact_hash", None)
    pack.artifact_hash = prefixed_hash("artifact", artifact)
    return pack
