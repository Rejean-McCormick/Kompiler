# Kompiler Framework v11 — opt-in, local derived context reader

**Candidate (no production or public qualification).** Kompiler keeps its 0.8.0-alpha.1 historical v6/v7/v9/v10 readers and Context Pack protocol. This addition does not change the Kristal Framework specification, Kit, Integration Pack or any canonical file.

## Boundaries

- **Framework v11.0.0-draft.4** validates KQ/KP/KA/KS graph identities; lexical dictionaries and exact Wikidata crosswalks remain separate.
- **Integration Pack 0.3.0-alpha.1** produces `kristal.integration.read-view/v11.0-draft.1` after verifying 13 pinned Framework files and running Framework's reference graph/dictionary validators.
- **Kompiler** requires an explicit local manifest with `local_read_approved = true`. It checks SHA-256 of the exact Pack script and pin before running them, builds the view in a temporary directory, checks digests and display/assertion references again and adapts *selected* IDs into derived Context Pack records. Neither source files nor approval state are mutated.
- `requested_locale` and `lexical.status` (`direct`, `fallback`, `missing`) stay separate from identities. A missing translation produces **no invented term**. `accepted_external_exact` remains a crosswalk annotation, never a primary identity.
- A KQ/KP identity is a record, KA assertion preserves subject, predicate, entity/literal object, qualifiers and KS references. A KS reference never implies a verified physical source locator. This adapter does **not** synthesize v9 epistemic statuses, authorization or publication.
- This is a **local reader only**. API listening on non-loopback is refused when this adapter is configured. No automatic discovery; no hosted/public catalog; no remote trust or role grants. Anyone allowed to use this local Kompiler instance can access the explicitly admitted IDs; isolate the host and do not register private sources in a multiuser instance.
- Guard and Pack validation verify structure, digests and supported semantics, **not authorization to disclose, license rights or truth**. The operator must authorize the scope of the selected local workspace separately.

## Install

Keep the reviewed Framework and Pack as sibling directories; do not copy normative schemas into Kompiler. Windows Python 3.12+ with the Kompiler dependencies and `jsonschema` is required.

1. Copy `adapters/examples/kristal-v11-read-view.toml` to a private configuration folder; set the explicit source root, four input paths, and exact Framework / Pack roots. Start from a *trusted* local workspace. Do not use an unapproved real dataset in shared API mode.
2. Reference that manifest from your normal Kompiler configuration:

```toml
[adapters.v11]
manifest = "C:/mycode/private-config/kristal-v11.toml"

[api]
host = "127.0.0.1"
```

3. Check `kompiler capabilities --json --config C:/mycode/private-config/kompiler.toml`. Then run a query with explicitly selected IDs:

```json
{
  "protocol":"kompiler.query", "version":"1.1", "request_id":"v11-local-demo",
  "operations":[{"id":"v11-read","target":"KristalV11:ExplicitLocalExample","operation":"read",
    "params":{"locale":"fr-CA","semantic_ids":["KQ1001","KP2001","KA3001","KS4001"]}}]
}
```

Run using `kompiler run demo-query.json --config C:/mycode/private-config/kompiler.toml --output context-pack.json` or your existing local Python/Windows launcher. This records a **derived** Context Pack, not a canonical graph.

## Safety gates

An invalid graph, changed Framework pin/tool, changed Integration Pack script/pin, bad namespace or lexical record, missing source, unsupported locale, unknown requested ID, excessive selection, or invalid local access configuration fails closed. A modified graph/catalog recomputes the capability/cache fingerprint. No `D:` data, network acquisition or write-to-source command is involved.

The v11 adapter is intentionally **not auto-discoverable** from a local folder and has no GitHub reader/publication mode. Before any shared or public feature, implement separately approved per-principal policy and C1/C2 publication checks. There is no rule here that a public Konstellation projection can be republished automatically.

## Validation

```bash
# With the exact local reviewed Framework & Pack:
KOMPILER_V11_FRAMEWORK_ROOT=/path/to/Framework KOMPILER_V11_PACK_ROOT=/path/to/Pack \
  python -m pytest tests/integration/test_v11_derived_context.py -v
python -m pytest
```

`tests/integration/test_v11_derived_context.py` runs the real pinned Framework demo and checks both positive and failure cases if those environment variables are set; otherwise the cross-repo tests are explicitly skipped. It also includes fixture-only security tests that run unconditionally.
