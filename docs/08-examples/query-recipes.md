# Query Plan Recipes

These are structural recipes. Concrete targets/operations MUST exist in the active capability snapshot.

## Parallel breadth scan

```text
A ──┐
B ──┼──> compiler
C ──┘
```

Use independent operations with no `inputs`.

## Pipeline

```text
A → B → C
```

Use when B consumes normalized referents/results from A and C consumes B.

## Fan-out

```text
       ┌→ B
A ─────┼→ C
       └→ D
```

Useful when one discovery set should be analyzed by multiple domain Kristals.

## Fan-in

```text
B ──┐
C ──┼→ D
E ──┘
```

D receives selected outputs from multiple upstream operations. Capability must explicitly support that input cardinality.

## Bounded heavy query

Specify both operation and global budgets:

```json
{
  "budget": {"max_items": 1000, "max_bytes": 1500000},
  "operations": [
    {
      "id": "heavy",
      "target": "HumanBody",
      "operation": "cross_layer",
      "params": {},
      "budget": {"max_items": 400}
    }
  ]
}
```

## Conflict-focused query

Ask for an operation/projection advertising conflict/tension capability and set `return.include_conflicts=true`. The compiler preserves competing records instead of silently selecting one.

## Legacy v5 reader-policy query

Only use reader-policy fields when the active capability advertises them. Never assume `validated_only` means maximum certainty or universal truth.
