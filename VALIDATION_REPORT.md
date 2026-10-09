# Kompiler 0.8.0-alpha.1 — validation and compatibility

**Date:** 2026-10-08. **Base:** user-supplied Windows source distribution `Kompiler-0.7.0-alpha.3-Windows(1).zip`.

## What changed

- Kristal Framework `10.0.0-draft.3` is pinned to SHA-256 `1e516dd026bce754fd4f22b874ba2d603f64954831a1b5c754ecbb475d29020f` for the supplied snapshot. The old draft.2 lock is retained. Different draft.3 contract sets require an explicit operator pin.
- Optional deterministic `budget.selection_mode="lexical"` prioritizes topic-overlap *within* each target while maintaining per-target fairness. Default `balanced` behavior and legacy query hashes remain unchanged.
- Record selection no longer stops after a single too-large item if smaller items remain.
- GitHub read-surface verification rejects malformed base64, false byte counts, control characters, wrong slug/summary metadata, missing file roles; local content is never reused without re-reading and re-verifying it.

## Executed checks

- Python suite (offline, no Framework): PASS; the Framework-dependent tests are skipped by design.
- Python suite with the **actual supplied** `10.0.0-draft.3` Framework snapshot: PASS, including formerly draft.2-only version assertions updated for supported pins.
- Added isolated selection, profile/hash compatibility, hosted read-surface attack/tamper, and full Context Pack compilation regressions: PASS.
- Python source bytecode compilation: PASS.
- Synthetic CLI end-to-end `python -m kompiler self-test`: PASS (two records, one conflict, no gaps).
- Normative contract ownership check: PASS; no Kristal Framework schemas copied into Kompiler.
- Protocol JSON schema exports, docs and repository manifests refreshed at release packaging time.

## Honest scope limits

- No live GitHub API, private account, or Windows desktop build test was performed. GitHub transport is verified through mocked `gh api` calls and local directory fixtures.
- The Windows archive contains **Python source code and `Kompiler.pyw` launcher**, not a precompiled Windows `.exe`; Python 3.12+ and project dependencies are needed.
- The lexical overlap heuristic is *not* embedding-based semantic relevance, knowledge authority or a trust measure; the byte/token approximation stays 4 bytes per token.
- The GitHub collection reader remains read-only and does not synchronize or publish. The SHA-256 pin ensures byte matching for a chosen contract set, not a global authenticity statement about any Git repository.
