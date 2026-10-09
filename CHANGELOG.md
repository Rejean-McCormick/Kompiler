# Changelog

## 0.8.0-alpha.1 — 2026-10-08

- Added exact bundled contract-set SHA-256 for the uploaded v10 draft.3 Framework snapshot, while retaining the older draft.2 lock and explicit override for other draft.3 sources.
- Introduced deterministic opt-in lexical Context Pack selection (`budget.selection_mode`), preserving default query hashes and target fairness.
- Fixed premature record-budget exhaustion when later smaller records could still fit.
- Strengthened hosted read-surface integrity checks and made local content reads revalidate bytes after earlier reads.
- Added non-regression coverage for version pins, selection, path controls, source tampering, bad base64 and size mismatches.
- Retained the read-only, non-normative boundary and offline-first operation.


## 0.7.0-alpha.3 — 2026-10-08

- added optional, index-first read-only GitHub collection transport; explicit GitHub URLs work with an already authenticated `gh` CLI, with every file fetch pinned to an immutable commit;
- implemented `kristal.github-collection-index/1.0` discovery, `kristal.github-sync-manifest/1.0` and `kristal.github-read-surface/1.0` verification, exact file SHA-256 verification and cross-layer state identity checks;
- added `kompiler github catalog|files|read`, local collection adapter auto-discovery and opt-in remote collection adapter targets for Context Packs;
- bounded remote reads, explicit network policy, file-cache reuse and concurrent reader operations without a full repo clone;
- updated `.pyw` with a GitHub collection browser, hidden Windows subprocesses, new Framework directory default and explicit local Framework pinning action;
- retained exact `10.0.0-draft.2` pin and added fail-closed support for Framework `10.0.0-draft.3` with an independently supplied contract-set SHA-256 (no new Git commit asserted);
- kept Kompiler purely read-only and accessory: Manager sync, GitHub Bootstrap publication and Framework semantics remain external.

## 0.7.0-alpha.2 — 2026-10-07

- aligns Kompiler discovery with `kristal.local-workspace/3.2.0`;
- discovers Local Kit v9 states from `build/v9/state-snapshot.json` and the optional `state/state-snapshot.json` mirror;
- reads Local Kit logical artifacts from `build/v9/artifacts/`;
- preserves exact historical release selection: multiple `release/v9/states/**` snapshots are never collapsed into an implicit "latest" state;
- preserves the Local Kristal workspace root during adapter discovery so provenance reports the actual local surface (`build-v9`, portable mirror, release, legacy);
- keeps Kristal Manager inventory as discovery-only metadata and retains strict read-only boundaries;
- validates the integration against the pinned Kristal `10.0.0-draft.2` Framework and a real Local Kit 3.2 example.
- makes the release ZIP byte-for-byte reproducible with fixed archive metadata.

## 0.7.0-alpha.1 — 2026-10-07

- aligns Kompiler to Kristal `10.0.0-draft.2` with an exact external contract-set SHA-256 and Framework commit pin;
- adds read-only Kristal v10 Publication Bundle discovery/verification without taking publication or activation authority;
- integrates optionally with `kristal-manager.json` for local path discovery only;
- adds `kompiler locals` and optional Manager auto-discovery;
- keeps Kristal Manager responsible for local inventory/backup and Kristal GitHub Bootstrap/Setup responsible for qualify/publish/activate;
- keeps Médiathèque kOA as the optional persistent source-byte authority upstream;
- removes stale vendored Kristal normative schema/example copies;
- test suite passes against the pinned Kristal v10 Framework.

## 0.6.0 — 2026-10-06

- adds read-only Kristal v9 State Snapshot / Logical Artifact discovery through the external Standard;
- advertises `V9-State-Reader` without claiming semantic, source, publication, or activation authority;
- preserves v6/v7/v8 compatibility and the external DaaT/Médiathèque/KQ-KP-KA-KS boundaries;
- removes stale vendored Kristal normative copies and uses an explicit draft-version pin until v9 RC/final restores an exact contract-set SHA-256 pin.

## 0.5.0 — 2026-10-03

- Aligns the external Kristal dependency to `7.0.0-draft.3.2` while preserving portable `kristal_state/6.0`.
- Defines Kompiler as a read-only context compiler, not a source acquisition/store, DaaT replacement, or Kristall semantic-identity authority.
- Documents **DaaT** as the human name and `daat` as the external machine identifier; DaaT is not a Kompiler runtime stage.
- Assigns persistent source bytes/snapshots to Médiathèque kOA and KQ/KP/KA/KS identity/crystallization to Kristal/Kristall.
- Removes built-in direct `source-catalog/` discovery and the legacy `kristal-foodbrands` raw catalog adapter.
- Clarifies that Kompiler normalization means adapter-output-shape normalization and that exact deduplication is Context-Pack-local, not global entity resolution.
- Removes stale vendored Kristal schemas/spec/examples that already violated the repository's external-contract ownership test.
- Bumps Python and desktop runtime versions to `0.5.0`.

## 0.4.0 — 2026-10-02

- Stops vendoring Kristal Standard schemas, normative docs, official examples and TCK vectors.
- Pins the external `kristal` monorepo at `7.0.0-draft.3.1` by contract-set SHA-256.
- Adds explicit `KOMPILER_KRISTAL_STANDARD_ROOT` / `[kristal_standard].root` configuration.
- Resolves v6/v7 schemas dynamically from the canonical Standard release.
- Adds draft3.1 Axis Type, KOS and TOC read operations to the Kristall adapter.
- Keeps Kompiler-owned protocol schemas local and unchanged in ownership.
- Bumps Python and desktop versions consistently to 0.4.0.

## 0.3.0 — Kristal v7 draft2 convergence

- advertises the Kristal v7 `V7-Projection` conformance profile without claiming the full `V7-Kristall` crystallization lifecycle;
- added a generic `kristal-v6-state` V7-Reader adapter that validates arbitrary portable v6 states without rewriting source bytes or replacing declared state identity;
- added native Kristall v7 meta-plane discovery and validation while preserving v6 source-state identity;
- vendored the Kristal Standard 7.0.0-draft.2 meta-artifact schemas and official example vectors;
- replaced the previous sorted-JSON fallback with an offline RFC 8785/JCS canonicalizer covered by the Kristal golden vectors, including UTF-16 key ordering;
- protocol 1.1 adds declarative per-operation Surface selectors with subject region, primary/secondary axes, context, source policy and preserved disagreement;
- capabilities now advertise meta-plane/v7-native/Surface requirements and runtime standard support;
- added a `kristall-v7` adapter exposing Surface, entity, Mesh, assertion-family, resonance, projection-recipe and manifest/meta reads;
- introduced deterministic `kompiler.generic-surface/1.0`, which requires real Mesh orientation-affinity structure rather than pretending an axis affected selection;
- Context Packs now preserve subjects, axes, assertion families, resonance observations and Surface descriptors as distinct collections;
- normalized records/relations preserve v7 semantic roles and Mesh edge semantics, preventing structural/similarity/path material from becoming facts;
- semantic resonance remains a non-authoritative candidate signal and never drives automatic identity resolution;
- added portable v7-to-v6 projection materialization with validated `extensions.kristal_v7` lineage;
- added `kompiler project-v6` and `/v1/projections/v6`;
- Kristall discovery can coexist with nested source Kristals in one inventory;
- v7 snapshot/source lineage participates in provenance, cache keys and deterministic context identity.

## 0.2.0 — correction and hardening pass

- semantic Context Pack identity is now independent of request IDs, run IDs, timestamps, durations, and cache-hit metadata;
- concrete serialized artifacts now have a distinct `artifact_hash`, and retained packs are persisted by artifact identity rather than semantic identity;
- Context Packs now expose `parent_context_pack_id` and the documented `empty` status;
- total Context Pack `max_bytes` and runtime-admin budgets are enforced against the complete canonical artifact, not records alone;
- operation cache identity now includes capability snapshot, source state, reader policy, locale, effective budgets/timeouts, upstream input hash, adapter identity, and semantic runtime configuration;
- unstable sources without a `state_id` no longer participate in result caching;
- join fan-in limits and network-default policy are enforced fail-closed;
- subprocess adapters now use bounded stream reads and process-tree cleanup on timeout/cancellation;
- native subprocess stdout limits are separated from semantic operation-result byte budgets;
- direct JSON adapters cache parsed documents and source-state hashes until underlying file metadata changes;
- source identities cover the principal projections actually queried by direct adapters;
- recursive, bounded Kristal discovery now finds nested/wrapped bundles and avoids symlink traversal;
- `adapters bootstrap` output is loaded automatically from the default generated config fragment;
- SQLite storage is serialized and thread-safe for a shared local API runtime; run rows distinguish semantic `context_pack_id` from concrete `artifact_id`;
- retention modes now honor `metadata`/`none` without persisting packs, while `packs` and `full` retain concrete artifacts;
- top-level graph edges are normalized into relations and cross-Kristal conflicts can surface when global subject/predicate IDs match;
- CLI admission validation and exit-code behavior now match the documented interface;
- local API error mapping, cancellation bookkeeping, task cleanup, and pack retrieval were hardened;
- impossible Context Pack budgets return HTTP 413, failed compilation is persisted as a failed run, and query/request/operation identifiers are constrained to non-empty values;
- missing Kristal identity files no longer produce a misleading empty-content source hash; adapter health surfaces missing identity paths;
- schema/release scripts were made self-contained and release building now regenerates schemas and documentation/repository manifests;
- expanded integration/unit coverage for API, retention, cache budget isolation, semantic determinism, discovery, network policy, join limits, global byte budgets, relations, and cross-target conflicts.

## 0.1.0 — initial reference implementation

- four v1 protocol artifact models and JSON Schemas;
- DAG planner/executor and constrained dataflow selectors;
- Context Pack compiler, provenance, conflict/gap handling and budgeting;
- SQLite cache/run metadata;
- CLI, local API, and React/Tauri UI;
- ten built-in Kristal adapters;
- documentation and test/conformance scaffolding.
