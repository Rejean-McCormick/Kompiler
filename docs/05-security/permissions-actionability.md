# Permissions, Actionability, and Human Boundaries

## Fundamental rule

Kristal v6 may represent actionability modes such as `automatic`, `human_review`, `human_decision`, `manual`, `prohibited`, `insufficient_information`, and `not_applicable`.

Kompiler preserves these values as knowledge. It does not treat them as runtime permissions.

```text
actionability = automatic
≠ authorization to modify a system
```

## Kompiler v1 is read-oriented

`kompiler.query/1.1` can invoke only capabilities with `read_only=true`.

A future action system would require a separate protocol with:

- explicit target-system ownership contract;
- authentication;
- admission/authorization check;
- human approval modes where required;
- idempotency;
- receipts;
- rollback/compensation semantics.

None of those are implied by Context Pack data.

## Human review

The desktop UI MAY require explicit user approval before running a large read query, especially when it accesses sensitive local Kristals or adapters that declare network use. This is a Kompiler safety/control policy and is separate from Kristal actionability metadata.
