# Local validation — Kompiler derived Framework v11 reader (2026-10-27)

Scope: code-only update of user-supplied `znapshot_Kompiler_10271222.zip` with exact local `Kristal Framework 11.0.0-draft.4` and `Kristal Integration Pack 0.3.0-alpha.1` from the supplied ecosystem snapshots. Nothing was uploaded to GitHub or executed on a Windows/VPS production environment.

## Verified behaviours

- Existing v6/v7/v9/v10 adapter implementations, discovery interfaces, query/context protocol, CLI, and Windows launcher preserved.
- Optional manifest-only `kristal-v11-read-view` adapter. No automatic v11 catalog discovery, source modification, network access, publication or implicit authority.
- Integrity guard of Integration Pack's exact `tools/v11_integration.py` and `contracts/v11-framework-pin.json`, plus Pack verification of the 13 pinned Framework v11 files.
- Real Framework sample graph → Pack derived read-view → Kompiler adapter → normalization → complete `kompiler.context-pack` compiled output.
- KQ/KP/KA/KS identity preservation; valid accepted exact external crosswalk, direct/fallback/missing lexical statuses, source evidence references, typed assertion payloads. Invalid or truncated input fails instead of inventing semantics.
- Existing v10 GitHub provenance tests were failing in the source ZIP because its included v10 patch had not been applied; the patch's additive fields were integrated without altering canonical content.
- Original external Framework v10 publication tests (requiring a suitable Framework v10 checkout) and hosting/policy/Windows tests remain separately gated; no false claims of those being exercised by the Framework v11 tests.

## Commands run

```bash
KOMPILER_V11_FRAMEWORK_ROOT=<exact-framework-checkout> KOMPILER_V11_PACK_ROOT=<exact-pack-checkout> python -m pytest
python scripts/check_contract_ownership.py
python -m compileall -q src/kompiler
python scripts/export_schemas.py
python scripts/build_docs_manifest.py
python scripts/build_manifest.py
```

`ruff` is not installed in this execution environment; static lint will run in the normal CI (`uv run ruff check src tests`). The archival SHA-256 manifest is a code-inventory control, not an authorization or independent security audit.

## Operational limitations

- **Local candidate only**. No production entitlement, C1/C2/C3 signature verification, Reader Policy, public URL, hosted catalog, auto-exposure, or Windows GUI wiring is included.
- The derived view is constructed from selected, explicitly admitted local source paths; all of its source inputs must be independently approved by the operator. A data reader does not confer ownership, rights or permission to disclose.
- Selection is bounded to 1,000 v11 context records; the generated view must be <=8 MiB. This is *not* full dump/scalability qualification.
- App/API binding is refused on non-loopback at runtime creation when this adapter is configured; local use still requires a trusted machine. No automatic prevention of a separately configured reverse proxy is claimed.
- Existing v10 independent Framework tests and large Skope/EncyK datasets are intentionally outside this qualification. `D:\EncyKlopedia` is never traversed or modified.
