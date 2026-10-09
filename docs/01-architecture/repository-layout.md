# Repository Layout

Current ownership-oriented structure:

```text
Kompiler/
├── README.md
├── LICENSE
├── pyproject.toml
├── docs/
├── schemas/
│   ├── kompiler-capabilities.schema.json
│   ├── kompiler-query.schema.json
│   ├── kompiler-context-pack.schema.json
│   └── kompiler-error.schema.json
├── src/kompiler/
│   ├── protocol/
│   ├── registry/
│   ├── planner/
│   ├── executor/
│   ├── adapters/
│   ├── kristall/              # v7 deployment reader + portable projection code
│   ├── normalization/         # adapter-output shape normalization only
│   ├── compiler/
│   ├── budgeting/
│   ├── provenance/
│   ├── storage/               # Kompiler cache/run metadata, not source storage
│   ├── api/
│   └── cli/
├── adapters/
│   └── examples/              # trusted manifest templates
├── config/
├── examples/                  # Kompiler-owned protocol examples only
├── tests/
└── desktop/
```

## Separation rules

- `schemas/` contains **only Kompiler protocol schemas**.
- Normative Kristal schemas/spec/TCK/examples are resolved from the externally pinned Kristal release and MUST NOT be vendored.
- `src/kompiler/adapters/` contains trusted **read-only knowledge/projection adapters**.
- `src/kompiler/normalization/` normalizes adapter output shape; it MUST NOT become a source-corpus cleaning pipeline.
- `src/kompiler/storage/` stores Kompiler cache/run/context artifacts only; it MUST NOT become the canonical source store.
- `src/kompiler/compiler/` remains domain-neutral and MUST NOT mint Kristall KQ/KP/KA/KS identity.
- direct application-owned `source-catalog/` integration is outside the built-in adapter boundary.
- domain-specific ranking belongs in adapter metadata or explicit policy plugins, not hardcoded in the generic compiler.
- test fixtures MUST be small synthetic or licensed samples; production Kristals and source stores are external inputs.

## External authority boundaries

`src/kompiler/kristal-standard.lock.json` pins the accepted Kristal/Kristall release, and `src/kompiler/kristal_standard.py` resolves the configured external Standard root.

Persistent source bytes/snapshots belong to Médiathèque kOA. DaaT (`daat`) is an optional external IK↔Kristal admission/contract-mapping boundary. Kristal/Kristall owns semantic identity and crystallization. See [Ecosystem Boundaries](ecosystem-boundaries.md).
