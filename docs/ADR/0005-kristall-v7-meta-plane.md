# ADR 0005 — Kristall v7 Is the Native Meta-plane

## Status

Accepted for Kristal Standard `7.0.0-draft.3.2` convergence.

## Decision

Kompiler treats Kristall v7 as a first-class meta-plane while preserving Kristal v6 states unchanged as source and portable projection contracts.

Kompiler Query Protocol 1.1 carries an explicit Surface selector. Context Packs preserve v7 subjects, axes, assertion families, Mesh semantics and semantic resonance in dedicated collections.

## Rejected alternatives

### Convert all v6 source states into a new v7 state format

Rejected because v7 explicitly preserves the v6 `kristal_state` wire contract and identity boundary.

### Flatten Mesh and resonance into ordinary facts

Rejected because v7 explicitly distinguishes factual assertions, structural relations, similarity/resonance signals, hypotheses and paths.

### Use free-text topic search as the portable v7 selector

Rejected as the normative path because v7 prefers stable subject regions and orientation axes. Free text can still be used inside domain adapters, but it is not a substitute for the v7 Surface contract.

## Consequences

- v6 adapters remain valid;
- Kristall adapters are additive;
- a deployment can expose both a Kristall and its source Kristals;
- portable projections remain v6-compatible and carry `extensions.kristal_v7` lineage;
- future draft changes require an explicit compatibility/version update.
