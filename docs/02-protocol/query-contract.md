# Query Plan Contract

`kompiler.query/1.1` is a declarative DAG of semantic operations.

## Minimal request

```json
{
  "protocol": "kompiler.query",
  "version": "1.1",
  "request_id": "pollution-001",
  "capability_snapshot_id": "cap:sha256:...",
  "operations": [
    {
      "id": "pollutants",
      "target": "Environment",
      "operation": "find",
      "params": {"topic": "air pollution"}
    }
  ]
}
```

## Full top-level shape

```json
{
  "protocol": "kompiler.query",
  "version": "1.1",
  "request_id": "...",
  "capability_snapshot_id": "...",
  "intent": "build_context",
  "topic": "pollution",
  "parent_context_pack_id": null,
  "operations": [],
  "context": {
    "reader_policy": null,
    "locale": "fr-CA"
  },
  "budget": {
    "max_items": 1200,
    "max_bytes": 1500000,
    "target_tokens": 120000
  },
  "execution": {
    "max_parallelism": 4,
    "default_timeout_ms": 30000,
    "on_operation_error": "fail_dependents"
  },
  "return": {
    "include_provenance": true,
    "include_raw_refs": true,
    "include_conflicts": true,
    "include_gaps": true
  }
}
```

## Operation

```json
{
  "id": "human_effects",
  "target": "HumanBody",
  "operation": "mechanisms",
  "params": {"scope": "health_effects"},
  "inputs": [
    {
      "from": "pollutants",
      "selector": "$.records[*].referent"
    }
  ],
  "budget": {"max_items": 300},
  "on_error": "fail_dependents"
}
```

### Required operation fields

- `id`: unique within request;
- `target`: exact advertised target ID;
- `operation`: exact advertised operation ID;
- `params`: object conforming to the capability's input schema.

### Inputs

`inputs` references prior operation results. v1 selectors are deliberately constrained. An implementation MUST NOT evaluate arbitrary code or general scripting expressions. The reference implementation supports a small declarative selector grammar over normalized fields.

### DAG rules

- references MUST point to existing operation IDs;
- self-reference is invalid;
- cycles are invalid;
- dependent operations run only after their required inputs are complete;
- sibling operations MAY run concurrently;
- ordering between independent operations MUST NOT affect normalized results.

`required=false` bindings may resolve to no data after an upstream failure. Required bindings whose upstream operation failed are not executed. An empty selection from a successful upstream operation remains valid data.

The reference runtime applies an administrator `max_join_items` limit to each selected binding before downstream injection.

## Error policies

Allowed v1 values:

- `abort_run` — any failure terminates the run;
- `fail_dependents` — failing node and dependent subtree fail; independent nodes continue;
- `continue` — failure is recorded and downstream nodes receive no input from that node unless their capability permits missing inputs.

`fail_dependents` is the recommended default.

## Read-only rule

The v1 Query Plan is read-oriented. A capability with `semantics.read_only=false` MUST NOT be invokable from `kompiler.query/1.1`. Future action protocols, if any, require a separate contract and explicit authority model.

## Forbidden fields

The core query contract has no `shell`, `command`, `python`, `javascript`, `sql`, `url_to_execute`, or arbitrary executable field. Domain-specific query strings are allowed only when an advertised capability explicitly defines and validates them as data.

## Query identity

`request_id` is an audit/transport identifier and is not part of the reference semantic Query Plan hash. Execution-only preferences that cannot alter content, such as cache usage and scheduling parallelism, are also excluded. Fields that can affect content or failure behavior remain part of semantic identity.

## Boundary constraints

A v1 Query Plan MUST contain a non-empty `request_id` and at least one operation. Each operation MUST have non-empty `id`, `target`, and `operation` strings. Operation IDs MUST be unique within the plan. These constraints are enforced at protocol parsing time before admission.

## Protocol 1.1: v7 Surface selector

`QueryOperation.surface` is optional for ordinary source-plane operations and required when the selected capability advertises `semantics.requires_surface=true`.

```json
{
  "surface": {
    "subject": {"subject_id": "subject:..."},
    "orientation": {
      "primary_axis": "KQ1001",
      "secondary_axis": "KQ1002"
    },
    "context": {},
    "source_policy": {},
    "conflict_policy": "preserve_disagreement"
  }
}
```

The Surface selector is semantic input: it participates in query hashing and cache identity. See [v7 Surface Contract](v7-surface-contract.md).
