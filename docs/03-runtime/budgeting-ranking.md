# Context Budgeting and Ranking

## Purpose

A successful query may retrieve more information than an LLM can use efficiently. Kompiler therefore treats context space as a finite compilation target.

## Budgets

Supported v1 budgets:

- `max_items` — hard budget across retained records and derived items;
- `max_bytes` — hard ceiling over the complete canonical Context Pack artifact;
- `target_tokens` — reference implementation uses a deterministic `4 bytes/token` proxy and applies it as an additional byte ceiling.

Runtime administrator limits clamp larger caller requests.

Operation-level budgets are enforced independently before normalization. Context-level budgeting then constrains the complete compiled artifact.

## Reference selection policy

The current deterministic reference policy:

1. exact-deduplicates records;
2. groups candidates by target;
3. selects round-robin across targets to preserve basic target coverage;
4. uses stable target/operation/record identifiers for ordering;
5. trims dependent relations/referents/sources to retained records;
6. keeps explicit gaps/failures and recomputes coverage metadata;
7. drops optional raw `operation_outputs` before sacrificing normalized records when the total byte ceiling is exceeded;
8. binary-searches the largest deterministic record prefix that fits;
9. trims adapter-derived diagnostics only after normalized records.

### Optional lexical mode (`0.8.0-alpha.1`)

Set `budget.selection_mode` to `"lexical"` on a `kompiler.query` request and provide a `topic`. When a request would otherwise exceed the record budget, records are ordered by deterministic case-folded word overlap between the topic and the records' content, statement and semantic ID, *within each source target*. Selection still alternates across targets and retains stable ties. If all records fit, the original record order is unchanged. This is lexical relevance, **not** semantic equivalence, confidence, trust or an authority ranking. `"balanced"` remains the default.

The selector computes per-record byte sizes, skipping oversized items so subsequent smaller records may still fit. The final full Context Pack byte limit is separately enforced after metadata and provenance are assembled.

```json
{"budget": {"max_items": 50, "max_bytes": 300000, "selection_mode": "lexical"}, "topic": "solar energy"}
```

## Truncation

Any operation truncation or Context Pack budget truncation sets `summary.truncated=true`, produces a `context_budget` gap when gaps are enabled, and yields `status="partial"`.

If the mandatory fixed metadata alone cannot fit inside the requested byte ceiling, compilation fails with `BUDGET_IMPOSSIBLE` rather than emitting an over-budget artifact.

## What ranking must not do

Default ranking must not equate popularity, source count, valuation magnitude, or actionability with truth or universal authority.
