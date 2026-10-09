# Storage, Cache, and Run History

## Source of truth

Kristals remain the source data. Kompiler's database is operational metadata, not a canonical knowledge store.

## SQLite responsibilities

The reference store contains:

```text
cache
runs
artifacts
```

It uses WAL mode, a busy timeout, and an in-process re-entrant lock around the shared `check_same_thread=false` connection so the local API can safely share one runtime across request threads.

## Cache key

A deterministic operation cache key includes:

```text
protocol major version
capability snapshot ID
adapter ID + version
source state/artifact identity
effective operation item/byte/timeout limits
normalized operation parameters
selected reader policy + locale
upstream input hash
runtime semantic config hash
```

Wall-clock timestamps and cache-hit state do not participate.

## Cache safety

A result is not reused when a stable `source.state_id` is unavailable. Source-state fingerprints are invalidated when watched source files change.

A bounded/truncated result generated under a smaller operation budget cannot satisfy a later request with a larger budget because effective limits participate in the cache key.

## Context Pack retention

Retention is independent from operation caching:

- `none` — no final pack artifact is retained; only minimal run completion state remains;
- `metadata` — run metadata/summary is retained, but not the Context Pack artifact;
- `packs` — final Context Packs are retained by `artifact_hash`;
- `full` — final packs plus bounded raw operation-output artifacts are retained.

The default is `metadata`.

Run rows distinguish semantic `context_pack_id` from concrete `artifact_id`.

## Export

Any retained pack can be exported as its JSON representation. Importing a previous pack does not make it trusted; schema and identities must be revalidated by the consumer.
