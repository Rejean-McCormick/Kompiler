# Kompiler derived read-context consumer — Branch 04 final-system integration

**Scope:** `TARGET_DESIGN` plus named local tests; not a public release, current Git HEAD or production assertion.

Kompiler uses opt-in `kristal-v11-read-view` on a **local** manifest and a reviewed Pack tool digest, not arbitrary direct canonical graph parsing. The authoritative source remains Framework/Kit; this adapter never registers or publishes a Kristal. Its output is a **derived** Context Pack containing original IDs/provenance and `publication_authorized: false`.

**Additional bilateral executable evidence:** `tests/integration/test_v11_cross_reader_preflight.py` runs a pinned Framework→Pack view generation, Kompiler adapter import and independent EncyKlopedia private-source preflight on the *same bytes*. The test also mutates an ID to a Wikidata Q value and requires receiver rejection. The campaign is opt-in: provide `KOMPILER_V11_FRAMEWORK_ROOT`, `KOMPILER_V11_PACK_ROOT`, and `KOMPILER_V11_ENCYKLOPEDIA_ROOT`; without them CI skips the cross-repository test rather than inventing installed checkouts.

**Pending:** a real authorized v11 release-index/privacy classification and C2/C4 per-collection publication contract. Do not turn this local test into a claim of public availability.

