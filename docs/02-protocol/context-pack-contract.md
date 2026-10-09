# Context Pack Contract

`kompiler.context-pack/1.1` is the primary product of a successful run.

## Goals

A Context Pack SHOULD be:

- self-describing;
- bounded;
- provenance-rich;
- epistemically faithful to source Kristals;
- easy for an LLM to consume;
- suitable for continued conversation and follow-up queries.

## Envelope

```json
{
  "protocol": "kompiler.context-pack",
  "version": "1.1",
  "context_pack_id": "ctx:sha256:...",
  "semantic_hash": "ctx:sha256:...",
  "artifact_hash": "artifact:sha256:...",
  "request_id": "pollution-001",
  "parent_context_pack_id": null,
  "generated_at": "2026-10-02T15:01:10Z",
  "status": "success",
  "topic": "pollution",
  "summary": {},
  "referents": [],
  "records": [],
  "relations": [],
  "derived": [],
  "conflicts": [],
  "gaps": [],
  "sources": [],
  "execution": {},
  "provenance": {}
}
```

## Record envelope

Kompiler does not force all Kristal versions into one false epistemic model. Instead, normalized records use a common wrapper plus a source-semantic payload.

```json
{
  "record_id": "kr:...",
  "kind": "assertion",
  "referent_ids": ["..."],
  "statement": {
    "subject": "...",
    "predicate": "...",
    "object": "..."
  },
  "epistemics": {
    "assertion_status": "sourced",
    "valuations": [],
    "certainty_level_legacy": null,
    "validation": null,
    "authority_recognition": null,
    "record_role": "reference_knowledge",
    "actionability": "not_applicable"
  },
  "coordinates": {},
  "applicability": {},
  "provenance_refs": ["prov:..."],
  "source_record_ref": "..."
}
```

For v6 sources, typed valuations/value states MUST be preserved when present. For v5 sources, `certainty_level_legacy`, validation, authority channel, reader policy, and related fields MUST be preserved when present. Adapters MUST NOT manufacture equivalence between a v5 certainty level and an arbitrary v6 valuation dimension unless a documented mapping profile explicitly defines it.

## Derived items

Derived items MUST declare their transform and inputs:

```json
{
  "derived_id": "drv:...",
  "kind": "aggregate",
  "value": 17,
  "transform": "count_distinct_referents/1.0",
  "input_refs": ["kr:a", "kr:b"]
}
```

A derived item is not a source assertion and MUST be labeled accordingly.

## Conflicts

Conflicts identify incompatible or tension-bearing records without selecting a winner unless an explicit deterministic policy does so.

```json
{
  "conflict_id": "conf:...",
  "record_refs": ["kr:a", "kr:b"],
  "basis": "incompatible_values",
  "resolution": "unresolved"
}
```

## Gaps

Gaps are explicit missing-context markers:

```json
{
  "gap_id": "gap:...",
  "question": "What evidence exists for long-term effects in children?",
  "basis": "requested_dimension_uncovered",
  "suggested_targets": ["HumanBody"]
}
```

## Execution metadata

The pack MUST include enough information to identify:

- Kompiler version;
- capability snapshot;
- normalized Query Plan hash;
- adapter versions;
- source Kristal state/artifact IDs when available;
- policies and budgets;
- partial failures;
- deterministic/non-deterministic declarations.

## Status

Allowed v1 values:

- `success` — requested plan completed within declared policy;
- `partial` — at least one useful result exists but one or more operations failed or were truncated;
- `empty` — execution succeeded but produced no visible records.

`context_pack_id` is the semantic identity and equals `semantic_hash` in the reference implementation. `artifact_hash` identifies the concrete serialized run artifact including audit metadata such as `request_id`, run ID, timestamps, durations, and cache-hit state. This separation permits reproducible semantic identity across independent reruns without overwriting concrete retained artifacts.

`parent_context_pack_id`, when present, links a follow-up compilation to the semantic Context Pack that motivated it. It does not imply automatic merging or inherited trust.

## Protocol 1.1: v7 meta-plane collections

A Context Pack may additionally contain:

```text
subjects
axes
assertion_families
resonance
surfaces
```

These collections are separate by design. They MUST NOT be flattened into factual `records` merely to simplify downstream consumption. `relations` also preserve v7 `edge_semantics`, status, source-assertion references, derivation record IDs, and resonance references when available.

`NormalizedRecord.semantic_role` distinguishes `source_assertion`, `derived_assertion`, `structural_relation`, `similarity_signal`, `hypothesis`, `path`, `entity`, and generic `record` material.
