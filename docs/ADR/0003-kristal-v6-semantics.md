# ADR 0003 — Kristal v6 Semantics Are First-class

## Status

Accepted.

## Decision

The common normalized model preserves v6 valuations, record roles, actionability, coordinates/applicability, provenance, validation, authority recognition, and state identity where present. v5 is supported through explicit legacy fields/mapping profiles.

## Rationale

Flattening these dimensions into generic `confidence` or `fact` fields would destroy information and can create false authority.

## Consequences

The Context Pack schema is richer than a conventional RAG result list. Cross-version mappings must be explicit and versioned.
