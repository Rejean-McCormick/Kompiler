# Reference Tech Stack

This document defines the **reference implementation stack**, not the protocol. Alternative implementations are conformant if they preserve protocol behavior.

## Backend/runtime

| Concern | Reference choice | Reason |
|---|---|---|
| Language | Python 3.12+ | Existing Kristal tooling is predominantly Python; strong JSON/data tooling; cross-platform |
| Packaging | `pyproject.toml` + `uv` | Reproducible local environments and fast dependency resolution |
| Typed models | Pydantic v2 | Strict protocol models, discriminated unions, schema generation |
| JSON Schema validation | `jsonschema` Draft 2020-12 | External artifact validation independent of Python model internals |
| Canonical JSON | RFC 8785 JCS (built-in implementation, optional `rfc8785` cross-check/backend) | Stable v7 meta hashing without requiring network/package availability |
| Hashing | SHA-256 | Compatible with existing Kristal content identity conventions |
| CLI | Typer | Typed command interface with good shell UX |
| Local API | FastAPI + Uvicorn | Optional local HTTP transport; same Pydantic models as core |
| Structured logs | Python `logging` or `structlog`-compatible JSON sink | Machine-readable run diagnostics |
| Durable metadata | SQLite | Local registry/cache/run metadata without external service dependency |
| Analytical staging | DuckDB, optional | Efficient local scans/joins for adapters that benefit from columnar execution |
| Tests | pytest + Hypothesis | Unit, integration, property, and protocol tests |
| Lint/type | Ruff + Pyright | Fast static quality gates |

## Desktop UI

The target desktop UI is intentionally thin:

- TypeScript;
- React;
- Vite;
- Tauri for desktop packaging if a native shell is desired;
- local API or subprocess/IPC transport to the Python runtime.

The UI MUST NOT implement query semantics independently. It edits/imports protocol artifacts, displays capabilities, starts runs, and renders diagnostics/results.

## Data formats

- JSON UTF-8 is the canonical protocol serialization for v1.
- Markdown is documentation only, not a wire format.
- JSONL MAY be used internally for streaming adapter outputs.
- SQLite stores metadata/cache; Kristals remain external source artifacts.

## Dependency policy

Core dependencies SHOULD remain small. Heavy analytical, vector, graph, or database engines belong behind optional extras or adapters unless they become required by a normative feature. RFC 8785 behavior is part of the core because Kristal v7 meta-artifact canonicalization depends on it; the repository carries golden-vector tests so the offline implementation cannot silently degrade to ordinary sorted JSON.

Suggested extras:

```text
kompiler[api]
kompiler[desktop]
kompiler[duckdb]
kompiler[dev]
```

## Explicit non-choice

Kompiler does not require a vector database. Semantic/vector retrieval may be implemented by an adapter, but the core architecture is structured-query-first.
