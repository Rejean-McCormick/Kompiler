# ADR 0002 — Declarative Semantic Query Plans

## Status

Accepted.

## Decision

LLMs submit semantic operations against advertised capabilities. They do not submit implementation commands.

## Rationale

This decouples the agent from heterogeneous Kristal CLIs, permits adapters to evolve, enables strict schema validation, and sharply reduces command-injection risk.

## Consequences

Adapter authors must invest in capability design and mapping. Native query tools remain implementation details.
