# Example: Multi-pass Context Compilation

## Pass 1 — broad context

The first Query Plan prioritizes breadth across several Kristals.

Resulting pack reports:

```json
{
  "gaps": [
    {
      "gap_id": "gap:children-pm25",
      "question": "Long-term PM2.5 evidence for children is under-covered.",
      "suggested_targets": ["HumanBody"]
    },
    {
      "gap_id": "gap-costs",
      "question": "Economic cost estimates are absent.",
      "suggested_targets": ["Economics"]
    }
  ]
}
```

## Pass 2 — fill selected gaps

The LLM emits a new plan:

```json
{
  "protocol": "kompiler.query",
  "version": "1.1",
  "request_id": "pollution-002",
  "parent_context_pack_id": "ctx:sha256:PASS1",
  "intent": "fill_context_gaps",
  "operations": [
    {
      "id": "children_health",
      "target": "HumanBody",
      "operation": "find",
      "params": {
        "topic": "PM2.5",
        "population": "children"
      }
    },
    {
      "id": "costs",
      "target": "Economics",
      "operation": "cost_estimates",
      "params": {"topic": "air pollution"}
    }
  ]
}
```

## Lineage

The second Context Pack includes `parent_context_pack_id`. A UI may offer a merged conversation view, but each pack remains independently hashable and auditable.

## Why separate passes

Multi-pass compilation lets the LLM spend context/query budget where the first structured result reveals actual uncertainty, rather than over-querying every possible dimension up front.
