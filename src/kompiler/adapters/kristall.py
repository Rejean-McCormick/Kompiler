from __future__ import annotations

from pathlib import Path
from typing import Any

from kompiler.adapters.base import Adapter, AdapterContext, AdapterResult
from kompiler.adapters.common import opcap
from kompiler.errors import AdapterError
from kompiler.kristall import KristallDeployment
from kompiler.protocol.canonical import prefixed_hash
from kompiler.protocol.models import OperationCapability, SourceDescriptor


def _ref_id(node: Any) -> str | None:
    return str(node.get("id")) if isinstance(node, dict) and node.get("id") else None


def _ref_kind(node: Any) -> str | None:
    return str(node.get("kind")) if isinstance(node, dict) and node.get("kind") else None


class KristallAdapter(Adapter):
    """Read-only Kristal Standard v7 meta-plane adapter.

    It does not infer identity from resonance and it does not turn Mesh paths into facts.
    The generic Surface policy is deliberately deterministic and exposed in metadata.
    """

    adapter_id = "kristall-v7"
    adapter_version = "0.2.0"
    kind = "kristall"

    def __init__(self, root: str | Path, target_id: str | None = None) -> None:
        self.root = Path(root).expanduser().resolve()
        self._deployment: KristallDeployment | None = None
        self._signature: tuple[tuple[str, int, int], ...] | None = None
        dep = self._load()
        self.target_id = target_id or f"Kristall:{dep.namespace_id}"

    def _file_signature(self) -> tuple[tuple[str, int, int], ...]:
        dep = self._deployment
        if dep is None:
            return ()
        paths = [dep.manifest_path, *dep.registry_paths.values()]
        out = []
        for p in sorted(set(paths), key=str):
            if not p.exists():
                continue
            st = p.stat()
            out.append((str(p), st.st_mtime_ns, st.st_size))
        return tuple(out)

    def _load(self) -> KristallDeployment:
        if self._deployment is None:
            self._deployment = KristallDeployment.load(self.root)
            self.root = self._deployment.root
            self._signature = self._file_signature()
            return self._deployment
        sig = self._file_signature()
        if sig != self._signature:
            self._deployment = KristallDeployment.load(self.root)
            self._signature = self._file_signature()
        return self._deployment

    def source_descriptor(self) -> SourceDescriptor:
        return self._load().source_descriptor()

    def health(self) -> dict[str, Any]:
        try:
            dep = self._load()
            return {"adapter_id": self.adapter_id, "target_id": self.target_id, **dep.health()}
        except Exception as exc:
            return {
                "ok": False,
                "adapter_id": self.adapter_id,
                "target_id": getattr(self, "target_id", "Kristall"),
                "root": str(self.root),
                "error": str(exc),
            }

    def capabilities(self) -> list[OperationCapability]:
        string = {"type": "string", "minLength": 1}
        return [
            opcap(
                "surface",
                "Compile a deterministic Kristall Surface from subject, orientation, context and policy.",
                {
                    "edge_semantics": {"type": "array", "items": string},
                    "include_candidates": {"type": "boolean"},
                    "allow_candidate_axes": {"type": "boolean"},
                    "resonance_min": {"type": "number", "minimum": 0, "maximum": 1},
                },
                semantic_plane="meta",
                requires_surface=True,
                v7_native=True,
                max_items=5000,
                record_kinds=["kristall_entity", "kristall_assertion"],
            ),
            opcap(
                "entity",
                "Resolve one native KQ entity and its immediate Mesh neighborhood.",
                {"entity_id": {"type": "string", "pattern": r"^KQ[1-9][0-9]*$"}},
                ["entity_id"],
                semantic_plane="meta",
                v7_native=True,
            ),
            opcap(
                "mesh",
                "Read Mesh edges without converting structural/similarity/path semantics into facts.",
                {
                    "node_id": string,
                    "relation": {"type": "string", "pattern": r"^KP[1-9][0-9]*$"},
                    "edge_semantics": {"type": "array", "items": string},
                    "status": {"type": "array", "items": string},
                },
                semantic_plane="meta",
                v7_native=True,
                record_kinds=["mesh_edge"],
            ),
            opcap(
                "assertion-families",
                "Read assertion families while preserving source membership and provenance.",
                {
                    "family_type": {"type": "array", "items": string},
                    "status": {"type": "array", "items": string},
                    "assertion_id": string,
                },
                semantic_plane="meta",
                v7_native=True,
                record_kinds=["assertion_family"],
            ),
            opcap(
                "resonance",
                "Read semantic resonance observations as non-authoritative candidate signals.",
                {
                    "ref_id": string,
                    "min_value": {"type": "number", "minimum": 0, "maximum": 1},
                    "status": {"type": "array", "items": string},
                },
                semantic_plane="meta",
                v7_native=True,
                record_kinds=["semantic_resonance"],
            ),
            opcap(
                "axis-types",
                "Read v7 axis-type definitions without treating them as instantiated axes.",
                {"axis_type_id": string, "status": {"type": "array", "items": string}},
                semantic_plane="meta",
                v7_native=True,
                record_kinds=["axis_type"],
            ),
            opcap(
                "kos",
                "Read external Knowledge Organization System registrations and mapping policy.",
                {"kos_id": string, "role": {"type": "array", "items": string}},
                semantic_plane="meta",
                v7_native=True,
                record_kinds=["kos_system"],
            ),
            opcap(
                "toc",
                "Read Kristall TOC categories/subjects while preserving KQ identity and external mappings.",
                {"subject_id": string, "category_id": string, "kind": {"enum": ["subjects", "categories", "all"]}},
                semantic_plane="meta",
                v7_native=True,
                record_kinds=["toc_subject", "toc_category"],
            ),
            opcap(
                "projection-recipes",
                "Read locally available v7 projection recipes.",
                {"recipe_id": string},
                semantic_plane="meta",
                v7_native=True,
                record_kinds=["projection_recipe"],
            ),
            opcap(
                "meta",
                "Return the Kristall manifest and registry inventory.",
                {},
                semantic_plane="meta",
                v7_native=True,
                max_items=100,
                record_kinds=["kristall_manifest", "registry_summary"],
            ),
        ]

    async def execute(self, operation: str, params: dict[str, Any], context: AdapterContext) -> AdapterResult:
        if operation == "surface":
            return self._surface(params, context)
        if operation == "entity":
            return self._entity(params, context)
        if operation == "mesh":
            return self._mesh(params, context)
        if operation == "assertion-families":
            return self._families(params, context)
        if operation == "resonance":
            return self._resonance(params, context)
        if operation == "axis-types":
            return self._axis_types(params, context)
        if operation == "kos":
            return self._kos(params, context)
        if operation == "toc":
            return self._toc(params, context)
        if operation == "projection-recipes":
            return self._projection_recipes(params, context)
        if operation == "meta":
            return self._meta(context)
        raise AdapterError("UNKNOWN_OPERATION", f"{self.target_id} does not expose operation {operation}")

    def _axes(self, dep: KristallDeployment) -> list[dict[str, Any]]:
        return [x for x in dep.registry("axes").get("axes", []) if isinstance(x, dict)]

    def _entities(self, dep: KristallDeployment) -> list[dict[str, Any]]:
        return [x for x in dep.registry("entities").get("entities", []) if isinstance(x, dict)]

    def _edges(self, dep: KristallDeployment) -> list[dict[str, Any]]:
        return [x for x in dep.registry("mesh").get("edges", []) if isinstance(x, dict)]

    def _assertions(self, dep: KristallDeployment) -> list[dict[str, Any]]:
        return [x for x in dep.registry("assertions").get("assertions", []) if isinstance(x, dict)]

    def _families_all(self, dep: KristallDeployment) -> list[dict[str, Any]]:
        return [x for x in dep.registry("assertion_families").get("families", []) if isinstance(x, dict)]

    def _resonance_all(self, dep: KristallDeployment) -> list[dict[str, Any]]:
        return [x for x in dep.registry("resonance").get("observations", []) if isinstance(x, dict)]

    def _sources_all(self, dep: KristallDeployment) -> list[dict[str, Any]]:
        return [x for x in dep.registry("sources").get("sources", []) if isinstance(x, dict)]

    @staticmethod
    def _limit(rows: list[Any], context: AdapterContext) -> tuple[list[Any], bool]:
        limit = context.max_items or len(rows)
        return rows[:limit], len(rows) > limit

    def _surface(self, params: dict[str, Any], context: AdapterContext) -> AdapterResult:
        if context.surface is None:
            raise AdapterError("SURFACE_REQUIRED", "Kristall surface operation requires operation.surface")
        dep = self._load()
        selector = context.surface
        subject_id = selector.subject.subject_id
        axis_ids = [selector.orientation.primary_axis]
        if selector.orientation.secondary_axis:
            axis_ids.append(selector.orientation.secondary_axis)

        subjects = dep.subjects()
        subject = next((x for x in subjects if x.get("subject_id") == subject_id), None)
        if subjects and subject is None:
            raise AdapterError(
                "UNKNOWN_SUBJECT_REGION",
                f"subject region {subject_id!r} is not declared by Kristall",
                {"available_subjects": [x.get("subject_id") for x in subjects]},
            )

        axes = self._axes(dep)
        axes_by_id = {str(x.get("axis_id")): x for x in axes if x.get("axis_id")}
        selected_axes: list[dict[str, Any]] = []
        for axis_id in axis_ids:
            axis = axes_by_id.get(axis_id)
            if axis is None:
                raise AdapterError(
                    "UNKNOWN_ORIENTATION_AXIS",
                    f"orientation axis {axis_id!r} is not registered",
                    {"available_axes": sorted(axes_by_id)},
                )
            if axis.get("status") != "active" and not params.get("allow_candidate_axes", False):
                raise AdapterError(
                    "INACTIVE_ORIENTATION_AXIS",
                    f"orientation axis {axis_id!r} is not active",
                    {"status": axis.get("status")},
                )
            selected_axes.append(axis)

        edges = self._edges(dep)
        include_candidates = bool(params.get("include_candidates", False))
        allowed_status = {"source_backed", "derived", "accepted"}
        if include_candidates:
            allowed_status.add("candidate")
        semantics_filter = set(params.get("edge_semantics") or [])
        usable_edges = [
            e
            for e in edges
            if e.get("status") in allowed_status
            and (not semantics_filter or e.get("edge_semantics") in semantics_filter)
        ]

        axis_affinity: dict[str, set[str]] = {axis: set() for axis in axis_ids}
        subject_entities: set[str] = set()
        for edge in usable_edges:
            left, right = edge.get("from"), edge.get("to")
            lid, rid = _ref_id(left), _ref_id(right)
            lkind, rkind = _ref_kind(left), _ref_kind(right)
            if edge.get("edge_semantics") == "orientation_affinity":
                for axis_id in axis_ids:
                    if lid == axis_id and rkind == "entity" and rid:
                        axis_affinity[axis_id].add(rid)
                    if rid == axis_id and lkind == "entity" and lid:
                        axis_affinity[axis_id].add(lid)
            if lkind == "subject" and lid == subject_id and rkind == "entity" and rid:
                subject_entities.add(rid)
            if rkind == "subject" and rid == subject_id and lkind == "entity" and lid:
                subject_entities.add(lid)

        primary_entities = axis_affinity[selector.orientation.primary_axis]
        if not primary_entities:
            raise AdapterError(
                "SURFACE_AXIS_UNBOUND",
                "primary orientation axis has no accepted orientation_affinity edges",
                {"axis_id": selector.orientation.primary_axis},
            )
        candidates = set(primary_entities)
        if selector.orientation.secondary_axis:
            secondary = axis_affinity[selector.orientation.secondary_axis]
            if not secondary:
                raise AdapterError(
                    "SURFACE_AXIS_UNBOUND",
                    "secondary orientation axis has no accepted orientation_affinity edges",
                    {"axis_id": selector.orientation.secondary_axis},
                )
            candidates &= secondary
        subject_mode = "declared_only"
        if subject_entities:
            candidates &= subject_entities
            subject_mode = "mesh_membership"
        if not candidates:
            raise AdapterError(
                "EMPTY_SURFACE_SELECTION",
                "subject and orientation selectors produced no common entities",
                {"subject_id": subject_id, "axes": axis_ids},
            )

        entities = [e for e in self._entities(dep) if e.get("entity_id") in candidates]
        entities.sort(key=lambda x: str(x.get("entity_id")))
        selected_entity_ids = {str(x["entity_id"]) for x in entities if x.get("entity_id")}

        selected_edges = []
        selected_assertion_ids: set[str] = set()
        for edge in usable_edges:
            left, right = edge.get("from"), edge.get("to")
            lid, rid = _ref_id(left), _ref_id(right)
            lkind, rkind = _ref_kind(left), _ref_kind(right)
            keep = (
                (lkind == "entity" and lid in selected_entity_ids)
                or (rkind == "entity" and rid in selected_entity_ids)
                or lid in axis_ids
                or rid in axis_ids
                or (lkind == "subject" and lid == subject_id)
                or (rkind == "subject" and rid == subject_id)
            )
            if not keep:
                continue
            selected_edges.append(edge)
            if lkind == "assertion" and lid:
                selected_assertion_ids.add(lid)
            if rkind == "assertion" and rid:
                selected_assertion_ids.add(rid)

        assertions = [
            a for a in self._assertions(dep) if str(a.get("assertion_id")) in selected_assertion_ids
        ]
        assertions.sort(key=lambda x: str(x.get("assertion_id")))

        families = []
        for family in self._families_all(dep):
            globals_ = {
                str(m.get("global_assertion_id"))
                for m in family.get("members", [])
                if isinstance(m, dict) and m.get("global_assertion_id")
            }
            if globals_ & selected_assertion_ids:
                families.append(family)

        active_refs = selected_entity_ids | set(axis_ids) | selected_assertion_ids | {subject_id}
        resonance_min = float(params.get("resonance_min", 0.0))
        resonance = []
        for obs in self._resonance_all(dep):
            refs = {_ref_id(obs.get("left")), _ref_id(obs.get("right"))}
            agg = obs.get("aggregate") or {}
            value = agg.get("value", 0.0) if isinstance(agg, dict) else 0.0
            if refs & active_refs and float(value or 0.0) >= resonance_min:
                resonance.append(obs)

        source_status = set(selector.source_policy.get("include_status") or ["active"])
        sources = [s for s in self._sources_all(dep) if s.get("status", "active") in source_status]
        manifest_sources = [
            s for s in dep.manifest.get("sources", [])
            if isinstance(s, dict) and s.get("status", "active") in source_status
        ]
        source_state_refs = sorted({str(s["state_id"]) for s in manifest_sources if s.get("state_id")})

        max_items = context.max_items or 5000
        entity_items = [
            {"kind": "kristall_entity", "semantic_id": e.get("entity_id"), **e} for e in entities
        ]
        assertion_items = [
            {
                "kind": "kristall_assertion",
                "semantic_id": a.get("assertion_id"),
                "semantic_role": "derived_assertion" if a.get("assertion_kind") == "derived" else "source_assertion",
                **a,
            }
            for a in assertions
        ]
        items = (entity_items + assertion_items)[:max_items]
        truncated = len(entity_items) + len(assertion_items) > max_items

        relation_rows = []
        for edge in selected_edges[:max_items]:
            left_id, right_id = _ref_id(edge.get("from")), _ref_id(edge.get("to"))
            if not left_id or not right_id or not edge.get("relation"):
                continue
            relation_rows.append(
                {
                    "relation_id": edge.get("edge_id"),
                    "subject_ref": left_id,
                    "predicate": edge.get("relation"),
                    "object_ref": right_id,
                    "edge_semantics": edge.get("edge_semantics"),
                    "status": edge.get("status"),
                    "source_assertion_refs": edge.get("source_assertion_refs", []),
                    "derivation_record_id": edge.get("derivation_record_id"),
                    "resonance_refs": edge.get("resonance_refs", []),
                }
            )

        referents = [
            {
                "referent_id": e.get("entity_id"),
                "label": e.get("preferred_label"),
                "kind": e.get("entity_kind"),
                "external_ids": e.get("external_ids", []),
            }
            for e in entities
        ]
        surface = {
            "surface_id": prefixed_hash(
                "surface",
                {
                    "snapshot_id": dep.snapshot_id,
                    "subject": selector.subject.model_dump(mode="json"),
                    "orientation": selector.orientation.model_dump(mode="json", exclude_none=True),
                    "context": selector.context,
                    "source_policy": selector.source_policy,
                    "conflict_policy": selector.conflict_policy,
                    "policy": "kompiler.generic-surface/1.0",
                },
            ),
            "kristall_id": dep.kristall_id,
            "namespace_id": dep.namespace_id,
            "subject": selector.subject.model_dump(mode="json"),
            "orientation": selector.orientation.model_dump(mode="json", exclude_none=True),
            "context": selector.context,
            "source_policy": selector.source_policy,
            "conflict_policy": selector.conflict_policy,
            "snapshot_id": dep.snapshot_id,
            "selection": {
                "policy": "kompiler.generic-surface/1.0",
                "subject_resolution": subject_mode,
                "selected_entity_count": len(selected_entity_ids),
                "selected_edge_count": len(selected_edges),
                "selected_assertion_count": len(selected_assertion_ids),
                "source_state_refs": source_state_refs,
                "path_semantics": "exploratory_not_assertive",
                "resonance_semantics": "candidate_signal_only",
            },
        }
        return AdapterResult(
            items=items,
            referents=referents[:max_items],
            relations=relation_rows,
            sources=sources[:max_items],
            assertion_families=families[:max_items],
            resonance=resonance[:max_items],
            axes=selected_axes,
            subjects=[subject] if subject else [{"subject_id": subject_id}],
            surfaces=[surface],
            metadata={
                "kristall_id": dep.kristall_id,
                "namespace_id": dep.namespace_id,
                "snapshot_id": dep.snapshot_id,
                "canonicalization_profile": dep.manifest.get(
                    "canonicalization_profile", "kristal.v7:jcs-rfc8785"
                ),
                "selection_policy": "kompiler.generic-surface/1.0",
            },
            raw_item_count=len(entity_items) + len(assertion_items),
            truncated=truncated or len(selected_edges) > max_items,
        )

    def _entity(self, params: dict[str, Any], context: AdapterContext) -> AdapterResult:
        dep = self._load()
        entity_id = str(params["entity_id"])
        entity = next((e for e in self._entities(dep) if e.get("entity_id") == entity_id), None)
        if entity is None:
            return AdapterResult(metadata={"entity_id": entity_id, "found": False})
        edges = [
            e
            for e in self._edges(dep)
            if _ref_id(e.get("from")) == entity_id or _ref_id(e.get("to")) == entity_id
        ]
        rows = []
        for edge in edges[: context.max_items or len(edges)]:
            s, o = _ref_id(edge.get("from")), _ref_id(edge.get("to"))
            if s and o and edge.get("relation"):
                rows.append({
                    "relation_id": edge.get("edge_id"),
                    "subject_ref": s,
                    "predicate": edge.get("relation"),
                    "object_ref": o,
                    "edge_semantics": edge.get("edge_semantics"),
                    "status": edge.get("status"),
                    "source_assertion_refs": edge.get("source_assertion_refs", []),
                    "derivation_record_id": edge.get("derivation_record_id"),
                    "resonance_refs": edge.get("resonance_refs", []),
                })
        return AdapterResult(
            items=[{"kind": "kristall_entity", "semantic_id": entity_id, **entity}],
            referents=[{
                "referent_id": entity_id,
                "label": entity.get("preferred_label"),
                "kind": entity.get("entity_kind"),
                "external_ids": entity.get("external_ids", []),
            }],
            relations=rows,
            metadata={"kristall_id": dep.kristall_id, "snapshot_id": dep.snapshot_id},
        )

    def _mesh(self, params: dict[str, Any], context: AdapterContext) -> AdapterResult:
        dep = self._load()
        rows = self._edges(dep)
        node = params.get("node_id")
        relation = params.get("relation")
        semantics = set(params.get("edge_semantics") or [])
        statuses = set(params.get("status") or [])
        if node:
            rows = [e for e in rows if _ref_id(e.get("from")) == node or _ref_id(e.get("to")) == node]
        if relation:
            rows = [e for e in rows if e.get("relation") == relation]
        if semantics:
            rows = [e for e in rows if e.get("edge_semantics") in semantics]
        if statuses:
            rows = [e for e in rows if e.get("status") in statuses]
        limit = context.max_items or len(rows)
        selected = rows[:limit]
        relations = []
        items = []
        for edge in selected:
            s, o = _ref_id(edge.get("from")), _ref_id(edge.get("to"))
            items.append({"kind": "mesh_edge", "semantic_role": self._edge_role(edge), **edge})
            if s and o and edge.get("relation"):
                relations.append({
                    "relation_id": edge.get("edge_id"), "subject_ref": s,
                    "predicate": edge.get("relation"), "object_ref": o,
                    "edge_semantics": edge.get("edge_semantics"), "status": edge.get("status"),
                    "source_assertion_refs": edge.get("source_assertion_refs", []),
                    "derivation_record_id": edge.get("derivation_record_id"),
                    "resonance_refs": edge.get("resonance_refs", []),
                })
        return AdapterResult(items=items, relations=relations, raw_item_count=len(rows), truncated=len(rows) > limit)

    @staticmethod
    def _edge_role(edge: dict[str, Any]) -> str:
        semantics = edge.get("edge_semantics")
        if semantics == "factual":
            return "source_assertion" if edge.get("source_assertion_refs") else "derived_assertion"
        if semantics == "similarity":
            return "similarity_signal"
        if semantics == "derivation":
            return "derived_assertion"
        return "structural_relation"

    def _families(self, params: dict[str, Any], context: AdapterContext) -> AdapterResult:
        dep = self._load()
        rows = self._families_all(dep)
        types = set(params.get("family_type") or [])
        statuses = set(params.get("status") or [])
        assertion_id = params.get("assertion_id")
        if types:
            rows = [x for x in rows if x.get("family_type") in types]
        if statuses:
            rows = [x for x in rows if x.get("status") in statuses]
        if assertion_id:
            rows = [
                x for x in rows
                if any(
                    isinstance(m, dict)
                    and (m.get("assertion_id") == assertion_id or m.get("global_assertion_id") == assertion_id)
                    for m in x.get("members", [])
                )
            ]
        selected, truncated = self._limit(rows, context)
        return AdapterResult(assertion_families=selected, raw_item_count=len(rows), truncated=truncated)

    def _resonance(self, params: dict[str, Any], context: AdapterContext) -> AdapterResult:
        dep = self._load()
        rows = self._resonance_all(dep)
        ref_id = params.get("ref_id")
        min_value = float(params.get("min_value", 0.0))
        statuses = set(params.get("status") or [])
        if ref_id:
            rows = [x for x in rows if ref_id in {_ref_id(x.get("left")), _ref_id(x.get("right"))}]
        if statuses:
            rows = [x for x in rows if x.get("status") in statuses]
        rows = [x for x in rows if float((x.get("aggregate") or {}).get("value", 0.0) or 0.0) >= min_value]
        selected, truncated = self._limit(rows, context)
        return AdapterResult(resonance=selected, raw_item_count=len(rows), truncated=truncated)

    def _axis_types(self, params: dict[str, Any], context: AdapterContext) -> AdapterResult:
        dep = self._load()
        rows = [x for x in dep.registry("axis_types").get("axis_types", []) if isinstance(x, dict)]
        axis_type_id = params.get("axis_type_id")
        statuses = set(params.get("status") or [])
        if axis_type_id:
            rows = [x for x in rows if x.get("axis_type_id") == axis_type_id]
        if statuses:
            rows = [x for x in rows if x.get("status") in statuses]
        selected, truncated = self._limit(rows, context)
        return AdapterResult(items=[{"kind": "axis_type", "semantic_id": x.get("axis_type_id"), **x} for x in selected], raw_item_count=len(rows), truncated=truncated)

    def _kos(self, params: dict[str, Any], context: AdapterContext) -> AdapterResult:
        dep = self._load()
        rows = [x for x in dep.registry("kos").get("systems", []) if isinstance(x, dict)]
        kos_id = params.get("kos_id")
        roles = set(params.get("role") or [])
        if kos_id:
            rows = [x for x in rows if x.get("kos_id") == kos_id]
        if roles:
            rows = [x for x in rows if x.get("role") in roles]
        selected, truncated = self._limit(rows, context)
        return AdapterResult(items=[{"kind": "kos_system", **x} for x in selected], raw_item_count=len(rows), truncated=truncated)

    def _toc(self, params: dict[str, Any], context: AdapterContext) -> AdapterResult:
        dep = self._load()
        toc = dep.registry("toc")
        mode = params.get("kind", "all")
        subject_id = params.get("subject_id")
        category_id = params.get("category_id")
        subjects = [x for x in toc.get("subjects", []) if isinstance(x, dict)]
        categories = [x for x in toc.get("categories", []) if isinstance(x, dict)]
        if subject_id:
            subjects = [x for x in subjects if x.get("subject_id") == subject_id]
        if category_id:
            categories = [x for x in categories if x.get("category_id") == category_id]
            subjects = [x for x in subjects if any(isinstance(p, dict) and p.get("category_id") == category_id for p in x.get("category_placements", []))]
        rows: list[dict[str, Any]] = []
        if mode in {"all", "categories"}:
            rows.extend({"kind": "toc_category", "semantic_id": x.get("category_id"), **x} for x in categories)
        if mode in {"all", "subjects"}:
            rows.extend({"kind": "toc_subject", "semantic_id": x.get("subject_id"), **x} for x in subjects)
        selected, truncated = self._limit(rows, context)
        return AdapterResult(items=selected, subjects=[x for x in subjects[: context.max_items or len(subjects)]], raw_item_count=len(rows), truncated=truncated)

    def _projection_recipes(self, params: dict[str, Any], context: AdapterContext) -> AdapterResult:
        dep = self._load()
        value = dep.registry("projection_recipes")
        rows: list[dict[str, Any]] = []
        if value.get("artifact_type") == "kristall_projection_recipe":
            rows = [value]
        elif isinstance(value.get("recipes"), list):
            rows = [x for x in value["recipes"] if isinstance(x, dict)]
        recipe_id = params.get("recipe_id")
        if recipe_id:
            rows = [x for x in rows if x.get("recipe_id") == recipe_id]
        selected, truncated = self._limit(rows, context)
        return AdapterResult(
            items=[{"kind": "projection_recipe", **x} for x in selected],
            raw_item_count=len(rows),
            truncated=truncated,
        )

    def _meta(self, context: AdapterContext) -> AdapterResult:
        dep = self._load()
        items = [{"kind": "kristall_manifest", **dep.manifest}]
        for name, value in sorted(dep.registries.items()):
            items.append({
                "kind": "registry_summary",
                "registry": name,
                "artifact_type": value.get("artifact_type"),
                "registry_id": value.get("registry_id") or value.get("mesh_id"),
                "count": self._registry_count(value),
            })
        selected, truncated = self._limit(items, context)
        return AdapterResult(items=selected, raw_item_count=len(items), truncated=truncated)

    @staticmethod
    def _registry_count(value: dict[str, Any]) -> int:
        for key in ("entities", "axes", "axis_types", "edges", "families", "properties", "assertions", "sources", "observations", "recipes", "systems", "categories", "subjects"):
            if isinstance(value.get(key), list):
                return len(value[key])
        return 1
