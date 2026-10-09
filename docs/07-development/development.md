# Development Guide

## Bootstrap

Reference workflow:

```bash
git clone <repo>
cd Kompiler
uv sync --all-extras
uv run pytest
uv run ruff check .
uv run pyright
```

## Local source setup

Production Kristals are external. Development uses configured local paths or small fixtures.

```toml
[adapters.humanbody]
root = "/absolute/path/to/Kristal-HumanBody/knowledge-base"
```

## Architectural dependency rule

Recommended dependency direction:

```text
protocol ← registry ← planner ← executor
                         ↑       ↓
                      adapters → normalization → compiler → output
```

The protocol package MUST NOT import concrete adapters.

## Pure functions

Normalization, hashing, selector evaluation, ranking, and most compilation transforms SHOULD be pure functions. This makes reproducibility and golden tests practical.

## Time

Wall-clock time is injected through a clock abstraction for tests. Generated timestamps do not affect semantic result identity unless explicitly defined.

## Randomness

Core v1 algorithms SHOULD use no randomness. If a future optional algorithm does, the capability/policy MUST declare it non-deterministic or provide an explicit seed included in run identity.
