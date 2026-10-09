# ADR 0004 — No Arbitrary Shell in Agent-facing Contracts

## Status

Accepted.

## Decision

No Kompiler v1 protocol message can carry an arbitrary shell command or executable path.

## Rationale

The LLM is an untrusted planner. Execution details belong to trusted local adapters. This is both safer and more portable.

## Consequences

Subprocess adapters use fixed executable/script mappings and argument vectors. New native commands require adapter changes, not arbitrary query-plan strings.
