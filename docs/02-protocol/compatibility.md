# Kristal Compatibility

Kompiler `0.5.x` targets **Kristal Standard 7.0.0-draft.3.2** as its native meta-orchestration layer while preserving the v6 source/projection contract unchanged.

## Compatibility hierarchy

```text
Kristal v5 query/runtime surfaces
        ↓ adapters
Kristal v6 kristal_state sources  ← preserved identity/wire semantics
        ↓ referenced by
Kristall v7 meta-plane            ← native Kompiler meta target
        ↓ Surface compilation
Kompiler Context Pack 1.1
        ↓ optional materialization
v6 kristal_state + extensions.kristal_v7
```

## v7 first-class meta semantics

Kompiler preserves, when present:

- native opaque `KQ`, `KP`, `KA`, and `KS` identities;
- reversible source-referent mappings;
- assertion families and their provenance;
- subject regions;
- primary and optional secondary orientation axes;
- Mesh `edge_semantics` and edge status;
- derivation lineage;
- semantic resonance as a non-authoritative signal;
- projection recipes and source-policy inputs;
- Kristall manifest/snapshot identity.

Kompiler MUST NOT treat resonance as identity, equivalence, truth, causality, authority, or permission.

## v6 source semantics remain unchanged

A v7 deployment can consume v6 `kristal_state` artifacts unchanged. Kompiler therefore continues to preserve:

- stable referents;
- assertion status;
- valuations and value semantics;
- coordinates and applicability;
- record role;
- actionability;
- evidence/source;
- validation and authority recognition;
- conflicts, succession and lineage;
- deterministic state identity.

The source v6 canonicalization/hash boundary remains separate from the v7 meta hash boundary.

## v5 adapter compatibility

Legacy Runtime Pack/query adapters may preserve:

- subject/predicate/object query semantics;
- assertion status and certainty fields;
- validation status;
- authority channels;
- reader-policy visibility;
- deterministic pagination/order;
- declared resource limits;
- constrained join behavior where exposed.

## No silent semantic coercion

Forbidden implicit mappings include:

```text
resonance high        ≠ identity
Mesh path             ≠ factual assertion
structural edge       ≠ source claim
v5 certainty=high     ≠ v6 actionability=automatic
validated             ≠ universal truth
v6 valuation high     ≠ permission to act
state hash valid      ≠ epistemically validated
```

Any cross-version mapping must be named, versioned, traceable and reversible to source fields.


## Contract ownership

Kristal Standard contracts are external and canonical in the `kristal` monorepo. Kompiler pins them by version + contract-set SHA-256 and does not carry local copies. A contract mismatch fails closed instead of silently accepting schema drift.


Kompiler 0.5 also narrows its ecosystem boundary: direct raw source-catalog integrations are not part of the runtime contract. Source authority belongs upstream; Kompiler consumes knowledge read surfaces and preserves provenance.
