# Kristall v7 Integration

## Status

Kompiler 0.5 targets **Kristal Standard 7.0.0-draft.3.2** as its native meta-orchestration model.

Kristal v7 is additive above v6. Kompiler therefore treats the two layers differently:

- a **Kristal** is a portable source state/projection, normally `kristal_state/6.0`;
- a **Kristall** is a v7 meta-orchestrator containing global semantic identities, registries, Mesh structure, assertion families, axes, subject regions and projection recipes.

Kompiler does not rewrite v6 states to make them v7. A v7 deployment references and composes source states while preserving their identity.


## Conformance profile

Kompiler 0.5 advertises **`V7-Projection`** as the highest Kristal v7 draft.3.2 conformance profile it currently implements. This means the runtime provides the V7-Reader and V7-Mesh foundations plus subject/orientation Surface generation and v6-compatible projection materialization.

It intentionally does **not** advertise `V7-Kristall`. Full crystallization responsibilities such as axis candidate discovery, structural promotion workflows, factorization across projections and reconstruction diagnostics are not silently claimed by the runtime. Those may be added behind an explicit future profile.

The generic `kristal-v6-state` adapter is the portable source boundary required by V7-Reader. It validates an arbitrary `kristal_state/6.0` artifact, preserves its bytes and declared `state_id`, and exposes source assertions without converting them into v7 identities.

## Supported v7 draft.3.2 artifacts

The bundled v7 reader validates and consumes:

- `kristall_manifest`;
- `kristall_entity_registry` (`KQ` identity space);
- `kristall_property_registry` (`KP` identity space);
- `kristall_assertion_registry` (`KA` identity space);
- `kristall_source_registry` (`KS` identity space);
- `kristall_assertion_family_registry`;
- `kristall_axis_registry`;
- `kristall_mesh`;
- `kristall_projection_recipe`;
- `kristall_crystallization_record`;
- `semantic_resonance_set`.

The runtime uses the v7 canonicalization profile `kristal.v7:jcs-rfc8785` for meta-plane snapshot identity. It never substitutes a v7 meta hash for a source v6 `state_id`.

## Agent-facing target

A discovered deployment is advertised as a `kind = kristall` target, conventionally:

```text
Kristall:<namespace_id>
```

Example:

```text
Kristall:kristall-main
```

Its capability descriptor marks v7-native operations with:

```json
{
  "semantic_plane": "meta",
  "v7_native": true
}
```

A Surface-producing operation additionally advertises:

```json
{
  "requires_surface": true
}
```

## Surface query

The v7-native `surface` operation requires a declarative Surface selector in the Kompiler Query Plan:

```json
{
  "id": "legal-power",
  "target": "Kristall:kristall-main",
  "operation": "surface",
  "surface": {
    "subject": {
      "subject_id": "subject:power-canada-quebec"
    },
    "orientation": {
      "primary_axis": "KQ2001"
    },
    "context": {},
    "source_policy": {
      "include_status": ["active"]
    },
    "conflict_policy": "preserve_disagreement"
  }
}
```

Exactly one primary axis is required. At most one secondary axis is accepted.

## Generic Surface policy

Kristal v7 draft.3.2 defines the semantics of Surfaces but intentionally does not mandate one storage engine or universal selection algorithm. Kompiler therefore exposes a deterministic implementation policy named:

```text
kompiler.generic-surface/1.0
```

The policy:

1. resolves the declared subject region;
2. resolves the primary and optional secondary orientation axes;
3. requires selected axes to be active unless the caller explicitly allows candidate axes;
4. uses accepted/source-backed/derived `orientation_affinity` Mesh edges to select entities;
5. intersects the primary and secondary affinity sets when two axes are declared;
6. applies subject Mesh membership when explicit subject-to-entity structure exists;
7. returns relevant Mesh edges without promoting them into factual assertions;
8. carries assertion families and resonance as separate meta-objects;
9. preserves source policy and source state references in the Surface descriptor.

If an axis has no usable `orientation_affinity` structure, the operation fails with `SURFACE_AXIS_UNBOUND` rather than pretending the axis affected the projection.

## Epistemic separation

Kompiler preserves the v7 invariant:

```text
source assertion
!= derived assertion
!= structural relation
!= similarity signal
!= hypothesis
!= path
```

Normalized records carry a `semantic_role`. Mesh relations retain `edge_semantics`, `status`, source assertion references, derivation records and resonance references.

Semantic resonance is emitted in the `resonance` collection. It is never converted into identity, factual truth, causality, authority or permission.

## Portable projections

Kompiler can materialize one Context Pack Surface as a portable v6 projection:

```bash
kompiler project-v6 context-pack.json -o projection.json
```

The result remains:

```json
{
  "schema_version": "6.0",
  "artifact_type": "kristal_state"
}
```

and carries v7 lineage under:

```text
extensions.kristal_v7
```

Only normalized records already represented as source assertions, derived assertions or hypotheses and containing a valid statement may become projection assertions. Structural Mesh relations, similarity signals and paths are excluded unless a future explicit derivation layer creates an assertion with lineage.

## Coexistence with source Kristals

Discovery does not stop when it finds a Kristall root. Source Kristals nested under the deployment can also be discovered and exposed as independent targets. This lets an agent choose between:

- direct source-level queries;
- v7 meta-plane Surface queries;
- mixed DAGs using both layers.

## Draft status

The target is `7.0.0-draft.3.2`, not a claimed final 7.0 release. Any future standard change that alters v7 artifact schemas or Surface semantics must be represented by a new compatibility profile rather than silently changing `kompiler.generic-surface/1.0`.
