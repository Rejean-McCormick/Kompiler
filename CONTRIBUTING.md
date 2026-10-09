# Contributing to Kompiler

Kompiler is protocol-first. Changes should preserve the separation between untrusted Query Plans, trusted adapters, source epistemics, and compiled context.

Before opening a change:

1. update protocol docs and schemas when wire behavior changes;
2. add or update tests for admission, deterministic identity, adapter normalization, and security boundaries;
3. keep domain-specific behavior inside adapters rather than the generic compiler;
4. do not add arbitrary execution fields to Query Plans;
5. document breaking semantic changes in `CHANGELOG.md` and an ADR when architectural.

Development setup:

```bash
uv sync --all-extras
uv run pytest
uv run ruff check src tests
```

Use repository issues/discussions for design and implementation coordination. Maintainer identities and private security contacts should be configured by the repository owner rather than invented in source documentation.
