from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from kompiler.adapters.base import AdapterResult
from kompiler.protocol.canonical import prefixed_hash, sha256_hex
from kompiler.protocol.models import (
    AssertionFamilyItem,
    Epistemics,
    NormalizedRecord,
    NormalizedRelation,
    OrientationAxisItem,
    Referent,
    ResonanceObservation,
    SourceDescriptor,
    SourceItem,
    SubjectRegionItem,
    SurfaceDescriptor,
)


@dataclass(slots=True)
class NormalizedBatch:
    records: list[NormalizedRecord] = field(default_factory=list)
    referents: list[Referent] = field(default_factory=list)
    relations: list[NormalizedRelation] = field(default_factory=list)
    sources: list[SourceItem] = field(default_factory=list)
    derived: list[dict[str, Any]] = field(default_factory=list)
    subjects: list[SubjectRegionItem] = field(default_factory=list)
    axes: list[OrientationAxisItem] = field(default_factory=list)
    assertion_families: list[AssertionFamilyItem] = field(default_factory=list)
    resonance: list[ResonanceObservation] = field(default_factory=list)
    surfaces: list[SurfaceDescriptor] = field(default_factory=list)


def _external_ref(value: Any) -> tuple[str | None, str | None]:
    if not isinstance(value, dict): return None, None
    ext = value.get("external_id") or value.get("id") or value.get("referent_id")
    label = value.get("label") or value.get("label_fr") or value.get("name") or value.get("title")
    return (str(ext), str(label) if label is not None else None) if ext else (None, str(label) if label is not None else None)


def _statement_refs(statement: dict[str, Any]) -> tuple[list[Referent], NormalizedRelation | None]:
    refs: list[Referent] = []
    subj = statement.get("subject")
    pred = statement.get("predicate")
    obj = statement.get("object")
    sid, slabel = _external_ref(subj)
    p = pred.get("external_id") or pred.get("id") or pred.get("label") if isinstance(pred, dict) else pred
    oval = obj.get("value") if isinstance(obj, dict) and "value" in obj else obj
    oid, olabel = _external_ref(oval)
    if sid: refs.append(Referent(referent_id=sid, label=slabel))
    if oid: refs.append(Referent(referent_id=oid, label=olabel))
    rel = None
    if sid and oid and p:
        rel = NormalizedRelation(relation_id="", subject_ref=sid, predicate=str(p), object_ref=oid)
    return refs, rel


def _source_record_ref(item: dict[str, Any]) -> str | None:
    for key in ("source_assertion_id", "assertion_id", "record_id", "id", "source_interaction_id", "loop_id", "pathway_id", "document_id", "code", "public_code_4"):
        if item.get(key) is not None:
            return str(item[key])
    return None


def _epistemics(item: dict[str, Any]) -> Epistemics:
    vals = item.get("valuations") or item.get("value_states") or []
    authority = item.get("authority_recognition") or item.get("recognition") or item.get("authority")
    return Epistemics(
        assertion_status=item.get("assertion_status") or item.get("status") if isinstance(item.get("status"), str) else item.get("assertion_status"),
        valuations=vals if isinstance(vals, list) else [vals],
        certainty_level_legacy=item.get("certainty_level") or item.get("certainty"),
        validation=item.get("validation") or item.get("validation_status"),
        authority_recognition=authority,
        record_role=item.get("record_role") or item.get("role"),
        actionability=item.get("actionability", "not_applicable"),
    )


def _semantic_role(item: dict[str, Any], kind: str) -> str:
    explicit = item.get("semantic_role")
    allowed = {"source_assertion", "derived_assertion", "structural_relation", "similarity_signal", "hypothesis", "path", "entity", "record"}
    if explicit in allowed:
        return str(explicit)
    if kind == "kristall_entity":
        return "entity"
    if kind == "kristall_assertion":
        return "derived_assertion" if item.get("assertion_kind") == "derived" else "source_assertion"
    if kind == "mesh_edge":
        semantics = item.get("edge_semantics")
        if semantics == "similarity":
            return "similarity_signal"
        if semantics == "factual":
            return "source_assertion" if item.get("source_assertion_refs") else "derived_assertion"
        return "structural_relation"
    if kind in {"hypothesis", "path"}:
        return kind
    return "record"


def normalize_result(target_id: str, operation_id: str, result: AdapterResult, source: SourceDescriptor) -> NormalizedBatch:
    batch = NormalizedBatch(derived=list(result.derived))
    seen_ref: dict[str, Referent] = {}
    seen_source: dict[str, SourceItem] = {}
    source_state = source.state_id or "unknown"
    root_source_id = f"source:{target_id}:{source_state}"
    seen_source[root_source_id] = SourceItem(source_id=root_source_id, title=target_id, target_id=target_id, source_state_id=source.state_id)

    for idx, raw in enumerate(result.items):
        item = raw if isinstance(raw, dict) else {"value": raw}
        source_ref = _source_record_ref(item) or f"row:{idx}"
        identity = {"target": target_id, "state": source_state, "source_ref": source_ref, "content": item}
        rid = prefixed_hash("kr", identity)
        statement = item.get("statement") if isinstance(item.get("statement"), dict) else None
        kind = item.get("kind") if isinstance(item.get("kind"), str) else ("assertion" if statement else "record")
        prov_id = prefixed_hash("prov", {"target": target_id, "state": source_state, "source_ref": source_ref})
        semantic_id = item.get("semantic_id") or item.get("entity_id") or item.get("assertion_id")
        record = NormalizedRecord(
            record_id=rid,
            kind=kind,
            semantic_id=str(semantic_id) if semantic_id is not None else None,
            semantic_role=_semantic_role(item, kind),
            target_id=target_id,
            operation_id=operation_id,
            statement=statement,
            content=None if statement else item,
            epistemics=_epistemics(item),
            coordinates=item.get("coordinates", {}) if isinstance(item.get("coordinates", {}), dict) else {"value": item.get("coordinates")},
            applicability=item.get("applicability", {}) if isinstance(item.get("applicability", {}), dict) else {"value": item.get("applicability")},
            provenance_refs=[prov_id, root_source_id],
            source_record_ref=source_ref,
            raw_ref=f"{target_id}:{source_ref}",
        )
        if statement:
            refs, rel = _statement_refs(statement)
            for ref in refs:
                seen_ref.setdefault(ref.referent_id, ref)
                record.referent_ids.append(ref.referent_id)
            if rel:
                rel.relation_id = prefixed_hash("rel", {"record": rid, "s": rel.subject_ref, "p": rel.predicate, "o": rel.object_ref})
                rel.record_ref = rid
                rel.provenance_refs = [prov_id]
                batch.relations.append(rel)
        else:
            # Common graph projections expose relations directly rather than wrapping
            # them as epistemic statements. Preserve those edges in the normalized graph.
            subject_ref = item.get("subject_ref") or item.get("source_ref")
            predicate = item.get("predicate") or item.get("predicate_ref") or item.get("relation")
            object_ref = item.get("object_ref") or item.get("target_ref")
            if subject_ref and predicate and object_ref:
                relation = NormalizedRelation(
                    relation_id=prefixed_hash(
                        "rel",
                        {
                            "record": rid,
                            "s": str(subject_ref),
                            "p": str(predicate),
                            "o": str(object_ref),
                        },
                    ),
                    subject_ref=str(subject_ref),
                    predicate=str(predicate),
                    object_ref=str(object_ref),
                    record_ref=rid,
                    edge_semantics=item.get("edge_semantics"),
                    status=item.get("status") if isinstance(item.get("status"), str) else None,
                    source_assertion_refs=item.get("source_assertion_refs", []) if isinstance(item.get("source_assertion_refs"), list) else [],
                    derivation_record_id=item.get("derivation_record_id"),
                    resonance_refs=item.get("resonance_refs", []) if isinstance(item.get("resonance_refs"), list) else [],
                    provenance_refs=[prov_id],
                )
                batch.relations.append(relation)
                for ref_id in (str(subject_ref), str(object_ref)):
                    seen_ref.setdefault(ref_id, Referent(referent_id=ref_id))
                    record.referent_ids.append(ref_id)
        batch.records.append(record)

        for ev in item.get("evidence_refs", []) if isinstance(item.get("evidence_refs"), list) else []:
            if not isinstance(ev, dict): continue
            sr = ev.get("source_ref", {})
            if not isinstance(sr, dict): continue
            sid = str(sr.get("id") or sr.get("source_id") or sr.get("source_url") or sha256_hex(sr))
            source_id = f"evidence:{sid}"
            seen_source[source_id] = SourceItem(source_id=source_id, title=sr.get("title"), url=sr.get("source_url") or sr.get("url"), target_id=target_id, source_state_id=source.state_id)
            record.provenance_refs.append(source_id)

    for r in result.referents:
        if not isinstance(r, dict): continue
        rid = r.get("referent_id") or r.get("id") or r.get("external_id")
        if rid:
            seen_ref[str(rid)] = Referent(referent_id=str(rid), label=r.get("label") or r.get("name"), kind=r.get("kind"), external_ids=list(r.get("external_ids", [])) if isinstance(r.get("external_ids", []), list) else [])
    for r in result.relations:
        if not isinstance(r, dict): continue
        s, p, o = r.get("subject_ref"), r.get("predicate") or r.get("predicate_ref"), r.get("object_ref")
        if s and p and o:
            batch.relations.append(NormalizedRelation(
                relation_id=str(r.get("relation_id") or prefixed_hash("rel", r)),
                subject_ref=str(s), predicate=str(p), object_ref=str(o),
                edge_semantics=r.get("edge_semantics"), status=r.get("status"),
                source_assertion_refs=r.get("source_assertion_refs", []) if isinstance(r.get("source_assertion_refs"), list) else [],
                derivation_record_id=r.get("derivation_record_id"),
                resonance_refs=r.get("resonance_refs", []) if isinstance(r.get("resonance_refs"), list) else [],
                provenance_refs=[root_source_id],
            ))
    for s in result.sources:
        if not isinstance(s, dict): continue
        sid = str(s.get("source_id") or s.get("id") or sha256_hex(s))
        payload = dict(s)
        payload.update({"source_id": sid, "target_id": target_id, "source_state_id": source.state_id})
        seen_source[sid] = SourceItem.model_validate(payload)
    for x in result.subjects:
        if isinstance(x, dict) and x.get("subject_id"):
            batch.subjects.append(SubjectRegionItem.model_validate(x))
    for x in result.axes:
        if isinstance(x, dict) and x.get("axis_id"):
            batch.axes.append(OrientationAxisItem.model_validate(x))
    for x in result.assertion_families:
        if isinstance(x, dict) and x.get("family_id") and x.get("family_type"):
            batch.assertion_families.append(AssertionFamilyItem.model_validate(x))
    for x in result.resonance:
        if isinstance(x, dict) and x.get("resonance_id"):
            batch.resonance.append(ResonanceObservation.model_validate(x))
    for x in result.surfaces:
        if isinstance(x, dict) and x.get("surface_id"):
            batch.surfaces.append(SurfaceDescriptor.model_validate(x))
    batch.referents = sorted(seen_ref.values(), key=lambda x: x.referent_id)
    batch.sources = sorted(seen_source.values(), key=lambda x: x.source_id)
    batch.relations.sort(key=lambda x: x.relation_id)
    batch.subjects.sort(key=lambda x: x.subject_id)
    batch.axes.sort(key=lambda x: x.axis_id)
    batch.assertion_families.sort(key=lambda x: x.family_id)
    batch.resonance.sort(key=lambda x: x.resonance_id)
    batch.surfaces.sort(key=lambda x: x.surface_id)
    return batch
