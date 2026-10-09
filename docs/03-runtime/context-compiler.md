# Context Compiler

The compiler transforms normalized operation outputs into a coherent Context Pack.

## Pipeline

```text
normalized adapter-output records
    ↓
referent indexing
    ↓
exact deduplication
    ↓
semantic grouping (only where declared)
    ↓
relation graph construction
    ↓
conflict/tension surfacing
    ↓
derived views
    ↓
coverage/gap analysis
    ↓
ranking + diversity
    ↓
budget selection
    ↓
Context Pack
```

## Exact deduplication

Records may be deduplicated **inside the compiled Context Pack** when their declared identity or normalized record content is identical. Source provenance is unioned, not discarded. This does not alter Médiathèque source storage or create Kristall semantic identity.

## Semantic merge

Two records that merely look similar MUST NOT be merged automatically. Semantic grouping requires stable upstream identity or an adapter-provided equivalence contract. Kompiler never invents KQ identity or global equivalence.

## Conflict handling

The compiler surfaces incompatible assertions/values when an explicit comparable dimension exists. It MUST NOT choose a winner based only on source count or a generic score unless an explicit versioned policy requests that behavior.

## Derived views

Transforms are pure, named, versioned functions. Examples:

- `count_distinct_referents/1.0`;
- `group_by_predicate/1.0`;
- `coverage_by_target/1.0`;
- `path_summary/1.0`.

Derived data MUST cite input record IDs.

## Gap analysis

Core deterministic gap rules may include:

- requested target returned zero records;
- requested dimension has no visible values;
- dependent query was skipped;
- source conflict remains unresolved;
- context budget removed an explicitly requested category.

The runtime does not require an LLM call to identify these gaps. An LLM may discover additional conceptual gaps later.

## Context Pack summary

The summary is structural metadata, not an AI-generated essay. Example:

```json
{
  "record_count": 497,
  "referent_count": 143,
  "relation_count": 812,
  "conflict_count": 18,
  "gap_count": 7,
  "targets": ["Environment", "HumanBody", "Power"]
}
```
