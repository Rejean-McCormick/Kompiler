# Engineering Principles

## 1. Compile context, do not dump data

A Context Pack is a compiled artifact. Query outputs from multiple Kristals/Kristall surfaces are normalized into a common record shape, deduplicated context-locally, linked, ranked, and budgeted while preserving provenance.

## 2. Capabilities before queries

Agents MUST query only operations advertised through `kompiler.capabilities`. Unknown targets, operations, parameters, or semantic dimensions fail closed.

## 3. Semantic requests, implementation-local execution

An untrusted request says:

```json
{"target":"HumanBody","operation":"mechanisms","params":{"topic":"PM2.5"}}
```

It does not say:

```json
{"shell":"python tools/query.py ..."}
```

Adapters own the mapping to CLI, library calls, indexed files, SQL, or another trusted local mechanism.

## 4. Preserve epistemic distinctions

Integrity, assertion status, valuation, validation, authority recognition, reader/view policy, actionability, and truth are not interchangeable. Kompiler MUST NOT flatten them.

## 5. Local-first

The reference runtime executes locally and treats remote access as optional adapter behavior. A network connection is not required by the core protocol.

## 6. Fail closed

Unsupported semantics MUST be rejected or surfaced as limitations. Kompiler MUST NOT silently coerce unknown value semantics, unsupported joins, invalid reader policies, or unknown operations.

## 7. Provenance survives compilation

Every normalized or derived item SHOULD carry enough lineage to identify its source Kristal, source state/artifact, adapter, operation, and upstream record identifiers.

## 8. Context is budgeted

The objective is not maximum recall at any cost. The objective is maximum useful, diverse, interpretable context within an explicit budget.

## 9. Transport is replaceable

Clipboard today and a direct agent integration tomorrow MUST use the same logical contracts.

## 10. Human boundaries remain explicit

Kompiler may report actionability. It never converts actionability into permission to mutate another system.
