# v7 Surface Contract

Kompiler Query Protocol 1.1 adds an optional per-operation `surface` member for Kristall v7 meta-plane operations.

## Shape

```json
{
  "surface": {
    "subject": {
      "subject_id": "subject:..."
    },
    "orientation": {
      "primary_axis": "KQ...",
      "secondary_axis": "KQ..."
    },
    "context": {},
    "source_policy": {},
    "conflict_policy": "preserve_disagreement"
  }
}
```

`secondary_axis` is optional and must differ from `primary_axis`.

A capability with `semantics.requires_surface=true` rejects a query that omits this structure. Conversely, source-plane operations reject an attached Surface selector so a v7 semantic control cannot silently be ignored.

## Hash boundary

The Surface selector participates in:

- the semantic Query Plan hash;
- the operation cache key;
- the Surface identity;
- Context Pack semantic identity.

Scheduling choices and cache-hit metadata do not participate in semantic identity.

## Context Pack additions

Protocol 1.1 adds dedicated collections:

- `subjects`;
- `axes`;
- `assertion_families`;
- `resonance`;
- `surfaces`.

They are intentionally not folded into `records` or `relations` because v7 requires epistemic separation between source assertions and meta-structure.
