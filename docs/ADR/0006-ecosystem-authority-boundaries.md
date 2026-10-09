# ADR 0006 — Ecosystem authority boundaries

**Status:** Accepted  
**Date:** 2026-10-03

## Decision

Kompiler is a context compiler only. It normalizes trusted adapter outputs into its internal protocol and compiles bounded Context Packs. It is not a source acquisition/store system, the DaaT mapping boundary, or a Kristall semantic-identity authority.

Persistent source bytes/snapshots belong to Médiathèque kOA. **DaaT** (`daat`) is an optional external IK↔Kristal admission/contract-mapping boundary. Kristal/Kristall owns KQ/KP/KA/KS identity, Mesh, axes, registries and crystallization.

Direct built-in discovery of application-owned `source-catalog/` directories is removed. Legacy source catalogs must be migrated to the appropriate source/knowledge authority before Kompiler consumes them.

Exact deduplication inside a Context Pack remains allowed because it is compilation-local and provenance-preserving. It MUST NOT be treated as semantic entity resolution.

## Consequences

- the `kristal-foodbrands` raw source-catalog adapter is removed from built-in discovery;
- Kompiler adapters are read-only knowledge/projection adapters;
- `normalization` means output-shape normalization, not corpus normalization;
- DaaT is documented but is not a Kompiler runtime stage;
- v7 KQ/KP/KA/KS identity never originates in Kompiler;
- the external Kristal Standard remains the sole normative contract source.
