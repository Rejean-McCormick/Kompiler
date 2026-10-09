# Determinism, Identity, and Provenance

## Determinism boundary

Kompiler does not promise that an LLM will generate the same Query Plan twice. It promises deterministic runtime behavior only for capabilities that declare determinism and when all declared semantic inputs are fixed.

## Query hash

The reference runtime hashes the semantic Query Plan. The request/audit identifier and execution-only scheduling/cache preferences are excluded. Semantic fields such as protocol version, capability snapshot, operations, dependency structure, parameters, reader context, error policy, timeouts, and budgets remain part of the identity when they can affect the result.

This allows two separately submitted requests with different `request_id` values to identify the same query semantics.

## Context Pack identities

Kompiler exposes two distinct identities:

```text
context_pack_id == semantic_hash == ctx:sha256:<semantic content>
artifact_hash                    == artifact:sha256:<serialized run artifact>
```

`semantic_hash` excludes transport/audit and wall-clock execution noise such as:

- request ID;
- run ID;
- generated timestamps;
- operation start/completion timestamps;
- durations;
- cache-hit flags.

It retains information that changes the compiled knowledge result, including source state, adapter version, operation status/error code, truncation, normalized content, compilation policy/config identity, and selected provenance.

`artifact_hash` hashes the concrete Context Pack serialization excluding only the `artifact_hash` field itself. Two reruns can therefore share one semantic identity while having distinct artifact identities.

## Persistence identity

Retained Context Packs are stored by `artifact_hash`. Run history stores both:

- `context_pack_id` — semantic identity;
- `artifact_id` — concrete retained artifact identity.

This prevents a later equivalent rerun from overwriting the concrete metadata of an earlier run.

## Provenance edge

Each normalized record SHOULD be traceable through:

```text
Context Pack record
  → operation receipt
  → adapter + version
  → source Kristal state/artifact
  → source record/assertion/evidence
```

## Source state identity

For v6, use the Kristal state identity contract rather than inventing an incompatible hash boundary. Direct-file adapters fingerprint the projections they query; fingerprints are reused while file metadata is unchanged and recomputed after source changes.

Operation caching is disabled when an adapter cannot provide a stable `source.state_id`.

## Reproducibility report

`kompiler inspect context-pack.json --reproducibility` reports semantic/artifact IDs, query/config hashes, cache hits, source state IDs, truncation, and whether successful receipts indicate an expected deterministic rerun.

## Kristal v7 meta canonicalization

Kristall v7 meta-plane identities use RFC 8785/JCS serialization. Kompiler's built-in canonicalizer is exercised against the Kristal JCS golden vectors, including UTF-16 property ordering and RFC number/string serialization. If the optional external `rfc8785` package is installed, the same canonical boundary can be delegated to it.

A Kompiler `source.snapshot_id` for a Kristall deployment is a **runtime snapshot identity**, not a replacement for a source v6 `state_id` and not an assertion that the Standard has defined a final artifact-specific v7 content-hash boundary. Source v6 identities remain untouched.
