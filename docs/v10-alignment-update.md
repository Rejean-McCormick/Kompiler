# Kompiler — Kristal v10 read-only alignment update

**Change type:** additive source provenance, tests, and documentation.
**Target:** the `Rejean-McCormick/Kompiler` `main` snapshot inspected at commit `2e6cca3941e1c8e199d21b494107b25a5daada7c` on 2026-10-12.
**Status:** local patch proposal, **not merged or deployed**.

## What was already implemented

Kompiler `0.8.0-alpha.1` already consumes a verified `kristal.github-collection-index/1.0` and the corresponding Manager-generated `kristal.github-sync-manifest/1.0`. It pins remote GitHub operations to the resolved full commit, checks read-surface SHA-256 and JCS digest, and does not sync, publish, activate or qualify a Kristal. Its `kristal-standard.lock.json` already contains the observed `10.0.0-draft.3.1` contract-set pin (`fd8add31bb0a20159fd2e6c6c3175863a8195c9840e0b9f6a8cc388e57176c92`). Do not replace these mechanisms with a second implementation.

## Changes in this proposal

| Change | Behavior | Reason |
| --- | --- | --- |
| Collection catalog metadata | Adds `source_revision` (remote exact Git SHA, or `null` for a local directory). | A Git transport revision must be explicit, never inferred from a local path. |
| File-map metadata | Adds `state_logical_commitment` and `source_revision`. | Readers can distinguish logical identity, transport revision and derived surface digest. |
| Verified file read | Adds `state_logical_commitment` and `source_revision` alongside existing `state_ref`, `surface_digest`, verified file SHA and source URI. | Each result retains enough metadata to trace its verified state without recrawling the collection index. |
| Adapter health | Adds `source_revision` from its existing pinned reader. | Diagnostic consistency. |
| English documentation | Clarifies Framework draft.3.1 support and limits of qualification. | Prior README wording still named only draft.2 and draft.3. |
| Tests | Exercises local and commit-pinned GitHub mocks without network. | Prevents future loss of state/provenance fields. |

These fields are additive metadata and **do not change** the `kompiler.context-pack` protocol, v9 canonical content, source bytes, data model, grants or GitHub repositories.

## Trust and coverage boundaries

- `state_logical_commitment` is read from the manifest and checked against the state, AI index, AI manifest and collection index in the existing reader. This is **observed declared identity**, not a new logical commitment created by Kompiler.
- `surface_digest` verifies the Manager-derived AI/hosting file list, not the existence of every external materialization.
- `source_revision` is a Git commit for a remote read, not a State Commitment. For local roots it is `null`, even if the directory happens to be inside Git.
- A successfully verified read does **not** prove independent C1 qualification, C2 consent, C3 publication, domain factual truth or source availability.
- The supplied `kristal-public` snapshot lacks its `kristals/index.json`. It cannot be treated as a fully qualified v10 collection until Manager and C3 deliver a verified index and sync manifest. Kompiler must fail closed rather than invent missing metadata.

## Verification after applying the patch

```bash
python -m pytest tests/integration/test_v10_provenance_metadata.py -v
python -m pytest tests/integration/test_github_collection.py tests/integration/test_github_reader_hardening.py tests/integration/test_c5_framework_pin.py -v
python -m pytest
python -m ruff check src tests
```

The repository CI and an end-to-end staging collection check remain required. The patch itself does not qualify or deploy a network collection.

## Not included (other repository owners)

- Kristal Framework contract evolution: owned by the Framework.
- `kristals/index.json`, sync manifests, public/private routing: owned by Manager and collection operators.
- C1/C2/C3 authorization or release automation: owned by KristalDiag, Bootstrap, and GitHub collection governance.
- Navigating all Kristals and their concepts: owned by Konstellation, using Kompiler's read-only Context Packs where appropriate.

**Apply only to the inspected repository revision or one where the guarded source anchors still match. Always review a Git diff before merging.**
