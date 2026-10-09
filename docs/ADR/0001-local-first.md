# ADR 0001 — Local-first Runtime

## Status

Accepted.

## Decision

The reference Kompiler runtime executes locally and does not require GitHub, cloud storage, or a hosted service.

## Rationale

- Kristals can be large and already exist locally.
- Clipboard/file transport is sufficient for the core LLM workflow.
- Local execution improves privacy and removes network latency/dependencies.
- Future direct integrations can use the same protocol over a different transport.

## Consequences

Remote/federated adapters remain possible but are optional and must declare network behavior.
