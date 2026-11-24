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
- **opt-in Framework v11 local derived-context reader** (`kristal-v11-read-view`) using exact Framework `11.0.0-draft.4` and Integration Pack `0.3.0-alpha.1` pins, with a trusted explicit local manifest, selected KQ/KP/KA/KS IDs, checked source/view hashes and lexical status preserved;
- optional Kristal Manager catalog discovery;
- Windows `Kompiler.pyw` control panel;
- ownership check preventing normative Kristal schemas from being re-vendored.

## v11 reader qualification limits

The v11 adapter is a **candidate local read-only projection**, not a normative implementation of Framework v11 or a certified public reader. It is not auto-discovered: the operator configures an explicit `adapters.v11.manifest` with `local_read_approved = true` and a loopback API. It validates the exact pinned Framework and Integration Pack source set; it cannot authorize disclosure, create canonical identities, write, publish, or activate a Kristal. Do not infer a missing lexical translation or external identity from a crosswalk. See [v11 derived context operations](../03-runtime/kristal-v11-derived-context.md).

For cross-repository v11 validation, supply real reviewed local checkouts and execute:

```bash
KOMPILER_V11_FRAMEWORK_ROOT=/path/to/Framework KOMPILER_V11_PACK_ROOT=/path/to/Pack \
  python -m pytest tests/integration/test_v11_derived_context.py -v
```

Without these exact local checkouts, the cross-repository cases are skipped; passing the remaining tests does not qualify a production or public reader.

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
