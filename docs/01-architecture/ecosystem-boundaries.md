# Ecosystem Boundaries

Kompiler is a **read/compile boundary**, not a source-ingestion or semantic-authority system.

```text
external sources
      │
      ▼
EncyK / acquisition layer
      │ durable source material
      ▼
Médiathèque kOA
  bytes / snapshots / hashes / rights / stable locators
      │
      │ owner-preserving references
      ▼
Interaction Kernel ──> DaaT (`daat`) ──> Kristal portable interface
                                      │
                                      ▼
                               Kristal / Kristall
                        semantic identity / registries /
                        Mesh / axes / crystallization
                                      │
                                      │ read surfaces
                                      ▼
                                  Kompiler
                         query / output normalization /
                         context graph / ranking / budget
                                      │
                                      ▼
                            kompiler.context-pack
```

The exact route may omit IK/DaaT for trusted local read-only access, but the ownership boundaries do not change.

## Kompiler owns

Kompiler owns:

- Query Plan validation and planning;
- trusted read-only adapter invocation;
- normalization of **adapter output shape**;
- exact duplicate removal inside one compiled context artifact;
- context-local grouping and relation assembly;
- conflict/gap surfacing;
- deterministic derived views;
- ranking, diversity and budget selection;
- Context Pack identity/provenance.

## Kompiler does not own

Kompiler does not:

- crawl, download or acquire source material;
- canonically clean or deduplicate a source corpus;
- persist source bytes/snapshots as a source authority;
- replace Médiathèque source identity or storage locators;
- act as the DaaT contract-mapping boundary;
- mint or merge Kristall KQ/KP/KA/KS semantic identity;
- author Kristall Mesh/axes/registries;
- perform crystallization;
- promote similarity/resonance/path signals into identity or truth.

## Meaning of normalization

The word **normalization** in Kompiler is intentionally narrow:

```text
heterogeneous adapter result
          ↓
common Kompiler record envelope
```

It does **not** mean:

```text
raw websites/files → cleaned canonical corpus
```

That upstream work belongs outside Kompiler.

## Context-local deduplication vs semantic identity

Kompiler may collapse byte/record-identical items inside a Context Pack while unioning provenance. This is an output-compilation optimization, not global entity resolution.

Two semantically similar records MUST remain distinct unless the upstream Kristal/Kristall contract already provides stable identity/equivalence semantics. Kompiler MUST NOT create a new KQ identity to make a merge possible.

## Source catalogs

Direct reads of application-owned `source-catalog/` directories are not a built-in Kompiler integration. Persistent source catalogs belong to Médiathèque kOA; source meaning exposed to reasoning belongs in Kristal/Kristall read surfaces.

Legacy domain packages may still expose source-policy metadata through a Kristal query API. Reading such metadata is acceptable; performing acquisition from it is not.

## DaaT

**DaaT** is the human-facing name; `daat` is the machine identifier.

DaaT is not embedded in the Kompiler runtime. When Interaction Kernel is used on the path into Kristal, DaaT performs admission and explicit contract mapping. Kompiler consumes the resulting knowledge read surface and remains read-only.

## Current Kristal toolchain boundaries

- **Kristal Local Kit**: local structure/check/build-v9.
- **Kristal Manager**: local inventory + validation + GitHub read-surface synchronization (public/private).
- **Kristal GitHub Setup/Bootstrap**: hosted network, qualification, publication and activation.
- **Kompiler**: read/query/context compilation only.

GitHub sync visibility and Manager catalog metadata are operational observations and never semantic authority.
