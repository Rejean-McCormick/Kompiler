# Example: Pollution Research Session

This example demonstrates the intended human ↔ LLM ↔ Kompiler loop.

## 1. Inventory

Kompiler advertises targets such as:

```text
Environment
Chemistry
HumanBody
Power
Economics
Law
```

The exact operations come from the current capability snapshot.

## 2. Human question

> Fais une réflexion approfondie sur la pollution : causes, mécanismes, conséquences et leviers.

## 3. LLM-generated Query Plan

```json
{
  "protocol": "kompiler.query",
  "version": "1.1",
  "request_id": "pollution-001",
  "capability_snapshot_id": "cap:sha256:EXAMPLE",
  "intent": "build_context",
  "topic": "pollution",
  "operations": [
    {
      "id": "pollutants",
      "target": "Environment",
      "operation": "find",
      "params": {"topic": "pollution", "limit": 300}
    },
    {
      "id": "chemistry",
      "target": "Chemistry",
      "operation": "mechanisms",
      "inputs": [{"from": "pollutants", "selector": "$.records[*].referent_ids[*]"}],
      "params": {"limit": 300}
    },
    {
      "id": "health",
      "target": "HumanBody",
      "operation": "mechanisms",
      "inputs": [{"from": "pollutants", "selector": "$.records[*].referent_ids[*]"}],
      "params": {"limit": 300}
    },
    {
      "id": "energy",
      "target": "Power",
      "operation": "relations",
      "params": {"relation": "emission_source", "limit": 200}
    }
  ],
  "budget": {
    "max_items": 1000,
    "max_bytes": 1500000,
    "target_tokens": 100000
  },
  "return": {
    "include_provenance": true,
    "include_conflicts": true,
    "include_gaps": true
  }
}
```

Operation IDs and parameters above are illustrative; a real LLM MUST use only the actual advertised capabilities.

## 4. Kompiler output

The Context Pack might summarize:

```json
{
  "status": "success",
  "summary": {
    "record_count": 497,
    "referent_count": 143,
    "relation_count": 812,
    "conflict_count": 18,
    "gap_count": 7
  }
}
```

## 5. Supercharged conversation

The user pastes the pack into the LLM and can now ask follow-ups such as:

- compare biological and economic consequences;
- distinguish causal mechanisms from correlations;
- identify conflicting evidence;
- adapt the explanation to a particular audience;
- ask Kompiler to fill one of the explicit gaps.

The expensive acquisition/structuring work does not need to be repeated for every follow-up while the pack remains in active context.
