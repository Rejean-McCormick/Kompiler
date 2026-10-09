from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from jsonschema import Draft202012Validator

from kompiler.errors import CompilationError
from kompiler.protocol.canonical import prefixed_hash
from kompiler.protocol.models import ContextPack, SurfaceDescriptor
from kompiler.kristal_standard import get_standard
_ALLOWED_STATUS = {"hypothesis","claimed","sourced","disputed","reviewed","validated","rejected","retracted","superseded"}
_ALLOWED_ROLES = {"authoritative_constraint","observed_state","organizational_rule","reference_knowledge","derived_state","decision","action","structural_record"}


def _surface(pack: ContextPack, surface_id: str | None) -> SurfaceDescriptor:
    if surface_id:
        found = next((x for x in pack.surfaces if x.surface_id == surface_id), None)
        if found is None:
            raise CompilationError("UNKNOWN_SURFACE", f"surface {surface_id!r} not found in Context Pack")
        return found
    if len(pack.surfaces) != 1:
        raise CompilationError(
            "SURFACE_SELECTION_REQUIRED",
            "portable v7 projection requires exactly one selected Surface",
            {"available_surfaces": [x.surface_id for x in pack.surfaces]},
        )
    return pack.surfaces[0]


def materialize_v6_projection(
    pack: ContextPack,
    *,
    surface_id: str | None = None,
    recipe_id: str = "recipe:kompiler-adhoc",
    projection_id: str | None = None,
) -> dict[str, Any]:
    surface = _surface(pack, surface_id)
    assertions: list[dict[str, Any]] = []
    for record in pack.records:
        if record.statement is None:
            continue
        if record.semantic_role not in {"source_assertion", "derived_assertion", "hypothesis"}:
            # v7 structural/similarity/path records MUST NOT silently become facts.
            continue
        statement = record.statement.model_dump(mode="json", exclude_none=True) if hasattr(record.statement, "model_dump") else record.statement
        assertion: dict[str, Any] = {
            "assertion_id": record.semantic_id or record.source_record_ref or record.record_id,
            "statement": statement,
            "record_role": record.epistemics.record_role if record.epistemics.record_role in _ALLOWED_ROLES else "derived_state",
            "actionability": record.epistemics.actionability if isinstance(record.epistemics.actionability, dict) else {"mode": "not_applicable"},
            "lineage": {"derived_from": [record.source_record_ref or record.record_id]},
        }
        if record.epistemics.assertion_status in _ALLOWED_STATUS:
            assertion["assertion_status"] = record.epistemics.assertion_status
        if record.coordinates:
            assertion["coordinates"] = record.coordinates
        if record.applicability:
            assertion["applicability"] = record.applicability
        if record.epistemics.valuations:
            assertion["valuations"] = record.epistemics.valuations
        if record.provenance_refs:
            assertion["provenance_refs"] = record.provenance_refs
        assertions.append(assertion)

    selected_refs = surface.selection.get("source_state_refs") if isinstance(surface.selection, dict) else None
    source_state_refs = (
        sorted({str(x) for x in selected_refs if x})
        if isinstance(selected_refs, list)
        else sorted({receipt.source_state_id for receipt in pack.execution.receipts if receipt.source_state_id})
    )
    projection_id = projection_id or prefixed_hash(
        "projection",
        {"context_pack_id": pack.context_pack_id, "surface_id": surface.surface_id, "recipe_id": recipe_id},
    )
    artifact: dict[str, Any] = {
        "schema_version": "6.0",
        "artifact_type": "kristal_state",
        "artifact_status": "working",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "assertions": assertions,
        "provenance": [],
        "extensions": {
            "kristal_v7": {
                "role": "projection",
                "kristall_id": surface.kristall_id or "unknown",
                "projection_id": projection_id,
                "subject": surface.subject.model_dump(mode="json"),
                "orientation": surface.orientation.model_dump(mode="json", exclude_none=True),
                "generated_from": {
                    "manifest_id": surface.kristall_id or "unknown",
                    "recipe_id": recipe_id,
                    "source_state_refs": source_state_refs,
                    "build_id": pack.artifact_hash or pack.context_pack_id,
                },
                "generated_at": pack.generated_at.isoformat().replace("+00:00", "Z"),
            }
        },
    }
    standard = get_standard()
    schema = json.loads(standard.portable_state_schema.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(artifact), key=lambda e: list(e.absolute_path))
    if errors:
        raise CompilationError(
            "INVALID_V6_PROJECTION",
            "materialized v7 portable projection failed v6 validation",
            {"errors": [{"path": list(e.absolute_path), "message": e.message} for e in errors[:32]]},
        )
    extension_schema = json.loads(standard.v7_extension_schema.read_text(encoding="utf-8"))
    extension = artifact["extensions"]["kristal_v7"]
    extension_errors = sorted(
        Draft202012Validator(extension_schema).iter_errors(extension),
        key=lambda e: list(e.absolute_path),
    )
    if extension_errors:
        raise CompilationError(
            "INVALID_V7_PROJECTION_EXTENSION",
            "materialized projection failed extensions.kristal_v7 validation",
            {
                "errors": [
                    {"path": list(e.absolute_path), "message": e.message}
                    for e in extension_errors[:32]
                ]
            },
        )
    return artifact
