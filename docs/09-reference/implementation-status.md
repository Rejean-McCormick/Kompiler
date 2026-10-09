# Implementation Status

## Current: `0.8.0-alpha.1`

The exact known Framework `10.0.0-draft.2` lock remains supported. Framework `10.0.0-draft.3` is pinned to the exact SHA-256 of the supplied 2026-10-08 snapshot. A different draft.3 contract set requires an explicit operator SHA-256; no Git commit is inferred.

Implemented:

- opt-in deterministic lexical Context Pack retrieval and fair source coverage;
- exact dual-version Framework lock and hardened GitHub source verification;

- protocol 1.1 Query/Capabilities/Context Pack runtime;
- local deterministic planner/executor, budgets, cache/storage and loopback API;
- external read-only Kristal contract loading;
- v6 portable-state compatibility;
- v7/v8 Kristall/query read surfaces;
- v9 State Snapshot reader;
- **Local Kit 3.2 workspace discovery** from `build/v9`, optional `state/` mirror and exact release directories;
- Local Kit logical-artifact reads from `build/v9/artifacts/`;
- v10 Publication Bundle verification/reader;
- optional Kristal Manager catalog discovery;
- Windows `Kompiler.pyw` control panel;
- ownership check preventing normative Kristal schemas from being re-vendored.

## Deliberately not owned

Kompiler does not own:

- Local Kristal inventory or GitHub synchronization — Kristal Manager;
- `build-v9` authoring — Kristal Local Kit;
- GitHub node/bootstrap, qualification, publication or activation — Kristal GitHub Setup/Bootstrap;
- source-byte authority — Médiathèque when used;
- KQ/KP/KA/KS identity, crystallization, truth or authority decisions — Kristal/upstream governance.

## Historical-release rule

Kompiler intentionally refuses to infer a "latest" historical local release when several `release/v9/states/**/state-snapshot.json` files exist. Use the current `build/v9` state or point to an exact release. This is required to avoid ambiguity in multi-state workspaces.

## Cross-repo verification

Run the full suite against the exact Framework checkout:

```bash
KOMPILER_KRISTAL_STANDARD_ROOT=../KristalV10 python -m pytest
```

Without the external Framework, tests that require normative Kristal schemas are skipped; Kompiler-owned protocol/runtime tests remain executable.

## Not claimed

- mutation/action authority;
- automatic identity resolution from similarity/resonance;
- publication or activation conformance;
- source acquisition;
- implicit selection of one historical Kristal release among several.

GitHub read-surface reader: `kompiler github catalog|files|read` and the optional `kristal-github-collection` query adapter (index-first, authenticated `gh api` remote reading, commit pinned, SHA-256 verified; no clone or mutation).
