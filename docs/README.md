# Kompiler Technical Documentation

Kompiler is a **local-first context compiler for AI systems**. It accepts declarative query plans produced by an LLM or a human, executes them against one or more Kristals through trusted adapters, and emits a structured **Context Pack** optimized for downstream reasoning.

This documentation is the technical source of truth for the Kompiler repository. The protocol is intentionally transport-independent: copy/paste, files, stdin/stdout, a local HTTP API, a desktop UI, MCP, or another future integration may all carry the same messages.

## Status

- Project: `Kompiler`
- Architecture status: reference implementation 0.8.0-alpha.1 + protocol 1.1 contracts
- Protocol family: `kompiler.*`
- Baseline Kristal compatibility: v7 draft.3.2 meta-plane native; v6 source/projection contract preserved; v5 query compatibility through adapters
- Deployment model: local-first, single-user by default
- Security posture: fail-closed, read-oriented, no arbitrary shell from untrusted query plans

## Documentation map

| Area | Documents |
|---|---|
| Overview | [Vision](00-overview/vision.md), [Principles](00-overview/principles.md), [Terminology](00-overview/terminology.md) |
| Architecture | [System Architecture](01-architecture/system-architecture.md), [Ecosystem Boundaries](01-architecture/ecosystem-boundaries.md), [Tech Stack](01-architecture/tech-stack.md), [Lifecycle](01-architecture/lifecycle.md), [Repository Layout](01-architecture/repository-layout.md) |
| Protocol | [Overview](02-protocol/protocol-overview.md), [Capabilities](02-protocol/capabilities-contract.md), [Query Plan](02-protocol/query-contract.md), [v7 Surface](02-protocol/v7-surface-contract.md), [Context Pack](02-protocol/context-pack-contract.md), [Errors](02-protocol/error-contract.md), [Compatibility](02-protocol/compatibility.md) |
| Runtime | [Execution Engine](03-runtime/execution-engine.md), [Adapter Contract](03-runtime/adapter-contract.md), [Kristal Integration](03-runtime/kristal-integration.md), [Kristall v7](03-runtime/kristall-v7.md), [Context Compiler](03-runtime/context-compiler.md), [Budgeting](03-runtime/budgeting-ranking.md), [Storage](03-runtime/storage-cache.md) |
| Interfaces | [CLI](04-interfaces/cli.md), [Local API](04-interfaces/local-api.md), [Desktop UI](04-interfaces/desktop-ui.md), [Transports](04-interfaces/transport.md) |
| Security | [Security & Trust](05-security/security-trust.md), [Determinism & Provenance](05-security/determinism-provenance.md), [Permissions & Actionability](05-security/permissions-actionability.md) |
| Operations | [Configuration](06-operations/configuration.md), [Observability](06-operations/observability.md), [Failure & Recovery](06-operations/failure-recovery.md), [Releases & Versioning](06-operations/releases-versioning.md) |
| Development | [Development](07-development/development.md), [Testing & Conformance](07-development/testing-conformance.md), [Adding an Adapter](07-development/adding-adapter.md), [Coding Standards](07-development/coding-standards.md), [Governance](07-development/governance.md) |
| Examples | [Pollution Session](08-examples/pollution-session.md), [Multi-pass Session](08-examples/multi-pass-session.md), [Query Recipes](08-examples/query-recipes.md) |
| Reference | [Implementation Status](09-reference/implementation-status.md), [Built-in Adapters](09-reference/built-in-adapters.md), [Adapter Manifests](09-reference/adapter-manifests.md), [Operator Workflow](09-reference/operator-workflow.md) |
| ADRs | [ADR index](ADR/README.md) |

## Core invariant

> **Kompiler compiles context. It does not acquire source corpora, store canonical sources, create semantic identity, truth, authority, or execution permission.**

A returned record means that the selected Kristal state, adapter, filters, and policy made the record visible. Kompiler MUST preserve epistemic metadata needed to interpret that record correctly.

- [GitHub collection reader](03-runtime/github-collection-reader.md) — read-only index-first GitHub/AI traversal and query-plan integration.
