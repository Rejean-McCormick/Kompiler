# Kompiler — English v10 Alignment Patch

**Target repository:** `Rejean-McCormick/Kompiler`  
**Inspected base commit:** `2e6cca3941e1c8e199d21b494107b25a5daada7c`  
**Status:** local, reviewable update; GitHub did **not** accept a branch creation (`403 Resource not accessible by integration`).

This bundle is an incremental update **for the existing Kompiler repository**, not a replacement repository. It preserves the current v10 reader, Framework pins and existing tests while adding traceable provenance to returned GitHub read-surface data.

## Preview, apply and test

From an existing local checkout of `Rejean-McCormick/Kompiler`:

```bash
python /path/to/Kompiler_v10_Alignment_Update_EN/scripts/apply_update.py /path/to/Kompiler
python /path/to/Kompiler_v10_Alignment_Update_EN/scripts/apply_update.py /path/to/Kompiler --apply --backup-dir /path/to/backup
cd /path/to/Kompiler
python -m pytest tests/integration/test_v10_provenance_metadata.py -v
python -m pytest
python -m ruff check src tests
git diff --check && git diff
```

The script is **dry-run by default** and refuses missing/changed anchors rather than guessing how to rewrite newer code. If the repository has uncommitted changes, save them before applying this update. Run the tests before committing anything.

## Included

- `scripts/apply_update.py` — exact-anchor, fail-closed local patcher;
- `tests/test_v10_provenance_metadata.py` — regression tests to install into `tests/integration/`;
- `docs/v10-alignment-update.md` — English architecture and qualification boundaries to install into `docs/03-runtime/`.

No network write, publication, activation, external canonical state mutation or version relabeling is performed by this bundle.
