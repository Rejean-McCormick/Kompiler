# Terminology

**Adapter** — Trusted local component translating a semantic Kompiler operation into a Kristal-native query mechanism.

**Capability** — Machine-readable declaration of a target's supported operation, parameters, output semantics, limits, and deterministic properties.

**Context Compiler** — Runtime stage that turns normalized operation outputs into a coherent Context Pack.

**Context Pack** — Structured, bounded artifact intended to become high-value working context for an AI system.

**DAG** — Directed acyclic graph of operations and dependencies in a Query Plan.

**Derived item** — A value or relation computed from source records by a declared transform. It is not a source assertion.

**Gap** — A missing or insufficiently supported information need detected by a deterministic rule or explicitly supplied by the caller. An LLM may also identify additional gaps after reading the pack.

**Kristal** — Portable structured epistemic state/projection. In the v7 architecture, source Kristals retain their v6 `kristal_state` identity and semantics.

**Kristall** — Kristal v7 meta-orchestrator over one or more source Kristals. It owns the global semantic namespace, registries, Mesh, subject regions, orientation axes and projection recipes; it does not replace source Kristal state identity.

**Mesh** — v7 meta-structure connecting semantic entities/assertions using typed edges whose epistemic role is preserved (`factual`, structural, similarity, identity-resolution, derivation, etc.). A path is not automatically a fact.

**Orientation axis** — v7 semantic orientation used to select/weight/organize a Surface. Exactly one primary axis is required for a portable v7 projection; one secondary axis may optionally be used.

**Surface** — Query-time v7 result produced from a subject region, orientation, context and policy. A Surface is a contextual view, not canonical truth.

**Semantic resonance** — Context-bound v7 alignment/dissonance signal. It MUST NOT be interpreted as identity, equivalence, truth, causality, authority or permission.

**Kompiler Runtime** — Local process that validates, plans, executes, normalizes, compiles, budgets, and emits protocol artifacts.

**Operation** — Semantic action advertised by an adapter, e.g. `find`, `dependencies`, `progression`, `mechanisms`.

**Query Plan** — Declarative `kompiler.query` message containing one or more operations and their dependency graph.

**Raw result** — Adapter-native output before normalization.

**Reader/View Policy** — Policy controlling which records are visible in a query surface. Visibility is not a truth decision.

**Referent** — Stable thing/concept/entity identity used by Kristal and preserved by Kompiler where available.

**Run** — One accepted Query Plan plus its execution metadata, outputs, diagnostics, and final pack/error.

**Target** — A capability namespace. It may be a source Kristal, a named projection, or a v7 Kristall meta-plane deployment.

**Valuation** — Kristal v6 typed evaluation on a dimension/value semantics/value-state axis. Kompiler preserves it rather than reducing it to a generic confidence score.

Normative words `MUST`, `MUST NOT`, `SHOULD`, `SHOULD NOT`, and `MAY` indicate required, recommended, discouraged, and optional behavior inside the Kompiler contract.
