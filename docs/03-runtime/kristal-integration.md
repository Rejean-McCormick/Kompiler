# Kristal Integration

## Integration stance

Kompiler is an **optional read-only context compiler**. It consumes Kristal read surfaces but does not manage Local Kristals, back them up, publish them, activate channels, or mint semantic identity.

```text
Médiathèque / sources
        ↓
Local Kristal
   ├─ Kristal Manager        inventory + GitHub read-surface sync
   ├─ Local Kit 3.2          check + build-v9
   └─ GitHub Setup/Bootstrap qualify + publish + activate
        ↓ read-only
     Kompiler
        ↓
kompiler.context-pack
```

The following invariants are preserved:

```text
LOCAL INVENTORY != SEMANTIC AUTHORITY
SYNC != PUBLICATION
PUBLICATION != ACTIVATION
CONTEXT PACK != KRISTAL CANON
HOST LOCATION != SEMANTIC IDENTITY
```

## External Standard pin

Normative Kristal schemas are not vendored. Kompiler loads them from the exact external Framework pin declared by `src/kompiler/kristal-standard.lock.json`. Draft.2 remains pinned to its exact known contract SHA-256; draft.3 and draft.3.1 each have their own exact contract-set SHA-256 pin from their respective source snapshots. A different contract set for either version requires an explicit independently verified operator SHA-256, rather than trusting a version string.

## Local Kit 3.2 discovery

When the input is a `kristal.local-workspace/3.2.0`, v9 selection is explicit:

1. `build/v9/state-snapshot.json` — current working build;
2. `state/state-snapshot.json` — optional portable-AI mirror;
3. legacy `.kristal/v9/...`;
4. legacy root `state-snapshot.json`;
5. `release/v9/states/**/state-snapshot.json` only when exactly one historical release exists.

Kompiler never decides that one of several historical releases is "latest" based on mtime or digest ordering. To query a particular historical release, give its directory or `state-snapshot.json` explicitly.

For a Local Kit current build, logical artifacts are read from `build/v9/artifacts/`. For an exact release, artifacts remain coupled to that release's sibling `artifacts/` directory. Source bytes are not rewritten.

## Kristal Manager catalog

`kristal-manager.json` is an operator-owned inventory, not semantic authority. With `[kristal_manager].auto_discover=true`, Kompiler uses catalog entries only as local paths to inspect. `sync_visibility`, `publication_target`, local Git status and other Manager metadata do not enter Kristal commitments or Context Pack source identity unless an upstream Kristal artifact already declares corresponding semantics.

## v9 State Reader

The `kristal-v9-state` adapter validates observed state/logical-artifact shapes against the external Framework schemas and exposes read-only `state` and `artifacts` operations. It preserves the declared `state_ref` and logical commitment.

## v10 Publication Reader

The `kristal-v10-publication` adapter accepts a local publication bundle containing:

```text
publication.json
bundle-manifest.json
state-snapshot.json
```

It validates v10/v9 schemas, payload byte digests, manifest binding, publication identity and publication→state binding before exposing `publication` and `state` reads. It does not create Releases or activate channels.

## Older compatibility surfaces

Kompiler still supports the portable v6 contract and the v7/v8 semantic/query substrate where adapters expose those forms. Compatibility does not grant Kompiler crystallization, truth, mutation or source-authority powers.

## DaaT and Médiathèque

DaaT (`daat`) remains an optional external Interaction Kernel admission/contract-mapping boundary. Persistent source bytes/snapshots belong to Médiathèque kOA when that subsystem is used. Kompiler may preserve opaque provenance/locator references but does not turn them into a new source store.

See [GitHub Collection Reader](github-collection-reader.md) for the added read-only lazy collection navigator and Context Pack adapter.
