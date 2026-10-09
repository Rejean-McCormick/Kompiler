# GitHub collection reader — Kompiler 0.8.0-alpha.1

Kompiler is a **read-only, optional** consumer of the GitHub/AI read surface. Kristal Local Kit owns construction of the exact `kristal.github-read-surface/1.0`; Kristal Manager owns `kristals/<slug>/` synchronization and `kristals/index.json`; GitHub Bootstrap/Setup owns CI ingestion, qualification, immutable publication and activation. The Framework defines the contracts and semantic identity. Kompiler creates **only Context Packs**.

## Retrieval model

```text
GitHub repository URL (public or permitted private) / local checkout
    ↓ (one compact index; no recursive crawl)
kristals/index.json
    ↓ choose matching slug / state_ref
kristals/<slug>/.kristal/sync-manifest.json
    ↓ verify target identity, manifest + ai/INDEX hashes
kristals/<slug>/AI_START_HERE.md → explicit selected files
    ↓ per-file size/SHA-256 verification
kompiler.context-pack
```

The remote implementation uses a **read-only GitHub CLI (`gh api`)**, not a clone and not a GitHub App. It resolves the requested ref to an immutable full Git commit SHA *before* downloading metadata. Every subsequent GitHub Contents API request is pinned to that SHA; for larger metadata the Git Blob API is used via the SHA from the commit-pinned Contents response. The session reuses small retrieved files. Private repos work only after the operator independently authenticates with `gh auth login` and has permission to read the repo.

The index is checked against the exact Manager `index_digest`, with identity/slug collision detection and deterministic ordering. Each Kristal has an independently verified `surface_digest` (JCS/SHA-256), plus byte hash verification of every file **actually read**. Kompiler checks `state_ref` and logical commitment consistency between the state, `AI_MANIFEST.json`, `ai/INDEX.json`, the sync manifest and collection index. It does not claim that those checks alone prove all referenced physical materializations are available; large blobs remain separate host-transport objects.

Untrusted source text is treated as evidence to compile, never as instructions to Kompiler. Kompiler does not execute code, workflows, commands or instructions read from GitHub.

## Direct CLI

```powershell
python -m kompiler github catalog https://github.com/Rejean-McCormick/kristal-public --query zoology
python -m kompiler github files https://github.com/Rejean-McCormick/kristal-public zoology
python -m kompiler github read https://github.com/Rejean-McCormick/kristal-public zoology AI_START_HERE.md
```

The same CLI works offline with a checked-out collection directory in place of the URL, including `C:\mycode\Kristal\kristal-public`. A CLI command is an explicit request for that resource and may use the network; query-plan auto registration remains subject to the default-deny network policy.

## Context Pack queries

To expose a remote collection as a query-plan target, opt in explicitly:

```toml
[runtime]
network_default = "allow"

[github]
collections = ["https://github.com/Rejean-McCormick/kristal-public"]
```

Or add a **local** collection root without enabling the network:

```toml
[github]
collections = ["C:/mycode/Kristal/kristal-public"]
```

Targets appear as `GitHubCollection:Rejean-McCormick:kristal-public` for remote and `GitHubCollection:kristal-public` for local. The adapter exposes `catalog`, `files`, `read` and `entrypoint` operations. They produce normal Kompiler Context Packs with provenance. `catalog` is the inexpensive discovery operation; use `read` only for relevant files.

```json
{
  "protocol": "kompiler.query",
  "version": "1.1",
  "request_id": "zoology-ai-start",
  "topic": "zoology",
  "operations": [
    {
      "id": "start",
      "target": "GitHubCollection:Rejean-McCormick:kristal-public",
      "operation": "entrypoint",
      "params": {"slug": "zoology"}
    }
  ]
}
```

## Performance and boundaries

- One index read lists thousands of Kristals; no full-tree crawl or per-Kristal API call for discovery.
- Direct reading opens only the selected manifest, AI integrity metadata, exact state and requested file; bounded session cache avoids repeated transfers.
- Maximum single read of 1 MiB; maximum collection index/metadata document of 8 MiB. Larger corpora need a paginated index extension or suitable materialization transport, not an unlimited download.
- No implicit download or copying of materialization blobs; no new derived Kristal commitments.
- Collection index and read-surface digests are **operational**, not semantic authority.
- Local checkouts are available in offline mode. Remote reading requires `gh` installed, authenticated and authorized.

## Framework lock

Existing `10.0.0-draft.2` remains pinned to its known exact contract-set hash. The observed `10.0.0-draft.3` and `10.0.0-draft.3.1` Framework snapshots have **distinct exact bundled contract-set SHA-256 pins**. Different contract sets using the same draft.3 version still require an explicit SHA-256 supplied by the operator. Supply the hash as `[kristal_standard].contract_set_sha256` or `KOMPILER_KRISTAL_CONTRACT_SET_SHA256`; the `.pyw` offers **Inspect / pin local Framework**, requiring explicit operator confirmation, for the current session.


In alpha.1, local file content is re-read and re-verified for every request, so modifications after the first read are not masked by a local byte cache. Remote reads remain cacheable only because the entire session is pinned to one immutable Git commit. Malformed base64, mismatched GitHub API byte counts, unsafe control characters and contradictory collection summaries are rejected.
