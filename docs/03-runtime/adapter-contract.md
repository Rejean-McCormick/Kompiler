# Kompiler Adapter Contract

## Purpose

An adapter translates semantic Kompiler operations into trusted **read-only knowledge/projection reads** and normalizes the returned shape. It does not acquire or canonically store source material.

## Required adapter interface

Conceptually:

```python
class Adapter:
    def describe(self) -> TargetCapability: ...
    def inspect_source(self) -> SourceSnapshot: ...
    def execute(self, operation: ResolvedOperation, ctx: RunContext) -> RawResult: ...
    def normalize(self, raw: RawResult, operation: ResolvedOperation) -> list[NormalizedRecord]: ...
    def health(self) -> HealthStatus: ...
```

The concrete Python interface MAY differ, but these responsibilities MUST remain observable.

## Adapter manifest

Each adapter has trusted local metadata:

```toml
id = "kristal-scolqc"
version = "1.0.0"
target_id = "ScolQc"
kind = "subprocess"
read_only = true

[source]
root = "/path/to/Kristal-ScolQc/knowledge-base"

[execution]
python = "/path/to/python"
script = "tools/query.py"
timeout_ms = 30000
```

Untrusted Query Plans cannot override `source.root`, executable paths, or adapter kind.

## Operation mapping

Adapter mappings are explicit. Example:

```text
Kompiler: target=ScolQc operation=progression
    ↓ trusted adapter mapping
Native:  python tools/query.py progression-grade <grade> <discipline?>
```

The adapter validates native preconditions and parses the exact output shape.

## Normalization requirements

An adapter MUST:

- preserve source IDs;
- preserve source epistemic labels;
- preserve provenance/evidence references when available;
- label adapter-derived fields;
- produce stable ordering when its capability declares determinism;
- reject malformed native output;
- never infer stronger validation or authority than source data states.

## Source identity

For Kristal v6 state files, adapters SHOULD verify declared identity when feasible before execution, using the active state identity contract. For legacy packs, use the strongest declared integrity mechanism available.

## Versioning

Changing an operation's semantic meaning is a breaking adapter capability change even if the native command name is unchanged.


## Authority boundary

Adapters MUST NOT turn Kompiler into a source crawler/store, DaaT replacement, or Kristall identity authority. Direct application-owned `source-catalog/` access is not a built-in adapter pattern. Source bytes/snapshots remain Médiathèque-owned; KQ/KP/KA/KS semantics remain Kristal/Kristall-owned.
