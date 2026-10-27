# Kompiler 0.8.0-alpha.1 — v11 derived reader candidate

Local-first, read-only context compiler. This repository contains the complete Kompiler source, its v6/v7/v9/v10 readers and an **opt-in Framework v11 local adapter**. This is a developer candidate, not a Framework conformance certificate or a public publication service.

## v11 local context reader (new)

The optional `kristal-v11-read-view` adapter delegates all validation to the exact **Kristal Framework 11.0.0-draft.4** and **Kristal Integration Pack 0.3.0-alpha.1** pinned binaries/scripts. It preserves **KQ/KP/KA/KS** identities, typed literals, direct/fallback/missing labels, source references and approved exact Wikidata crosswalk annotations. It never writes, activates, migrates or publishes a Kristal.

The adapter is **not auto-discovered**. Use an explicitly approved local manifest and a loopback Kompiler instance only. See [installation, operations and limitations](docs/03-runtime/kristal-v11-derived-context.md) and [the example manifest](adapters/examples/kristal-v11-read-view.toml).

## Existing features preserved

- Protocol `kompiler.query` 1.1 and derived Context Pack compilation, budgets and provenance.
- Kristal v6 state, v7/v8 Kristall surfaces, v9 State Snapshot and v10 publication bundle readers.
- Local workspace discovery (Kit 3.2), exact historical state selection, verified GitHub collection reader.
- Python API/CLI, local FastAPI and Windows `Kompiler.pyw` panel.
- Existing semantic, lexical, policy and publication authority boundaries remain external.

The snapshot also contained an un-applied **v10 provenance metadata patch** and its tests. This delivery integrates that additive read-metadata patch into the existing verified GitHub reader; local checkouts have `source_revision: null` and remote reads have a pinned Git commit. See [the original v10 note](docs/03-runtime/v10-alignment-update.md).

## Test commands

```bash
python -m pip install -e '.[dev,api]'
python -m pytest
# With local exact Framework & Pack checkouts:
KOMPILER_V11_FRAMEWORK_ROOT=/path/to/Framework KOMPILER_V11_PACK_ROOT=/path/to/Pack python -m pytest tests/integration/test_v11_derived_context.py -v
python scripts/check_contract_ownership.py
python -m ruff check src tests
```

Supported runtime: Python 3.12+; Framework and Pack must be installed separately, never vendored into this repository. CI qualification of historical v10 features requiring an external Framework remains conditional. No GitHub, VPS, canonical source, `D:` evidence or public library was changed by this update.
