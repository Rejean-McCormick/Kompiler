# System Architecture

## Component model

```text
                 ┌──────────────────────┐
                 │ LLM / Human / Agent  │
                 └──────────┬───────────┘
                            │ kompiler.query
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    Kompiler Runtime                     │
│                                                         │
│  Protocol Parser → Validator → DAG Planner              │
│                              ↓                          │
│                         Scheduler                       │
│                    ↙       ↓       ↘                    │
│            Source Adapter / Kristall v7 Adapter          │
│                    ↘       ↓       ↙                    │
│                    Normalization                        │
│                         ↓                               │
│        Context Graph / Merge / Conflict Surface         │
│                         ↓                               │
│            Ranking / Diversity / Budgeting              │
│                         ↓                               │
│                 Context Pack Builder                    │
└──────────────────────────┬──────────────────────────────┘
                           │ kompiler.context-pack
                           ▼
                 ┌──────────────────┐
                 │ LLM / downstream │
                 └──────────────────┘
```

## Trusted and untrusted boundaries

Untrusted inputs include:

- Query Plans emitted by an LLM;
- imported JSON files;
- text pasted into the desktop UI;
- local API requests from non-trusted clients.

Trusted code includes:

- protocol validation;
- adapter registry;
- adapter implementation mappings;
- approved executable paths;
- normalization code;
- local configuration.

Kristal data itself is **data**, not executable authority. A signed or validated artifact may affect visibility and interpretation but MUST NOT cause arbitrary code execution.

## Logical layers

### Protocol layer

Parses and validates `capabilities`, `query`, `context-pack`, and `error` envelopes.

### Registry layer

Discovers configured source-Kristal and Kristall v7 adapters and resolves capability IDs to exact adapter implementations. A Kristall target may coexist with the source Kristals it references.

### Planning layer

Checks references, detects cycles, computes topological stages, propagates budgets and policies, and rejects impossible plans before execution.

### Execution layer

Runs independent operations concurrently when safe and deterministic. Enforces time, row, byte, and join caps.

### Adapter layer

Owns Kristal-specific behavior. This is the only layer allowed to know native paths such as `knowledge-base/tools/query.py`.

### Normalization layer

Maps heterogeneous **adapter outputs** into a common internal record envelope without destroying source semantics. This is not source/corpus normalization and does not modify upstream source storage. In v7, subjects, axes, assertion families, Mesh edge semantics, resonance observations and Surface descriptors remain distinct meta-plane objects rather than being flattened into facts.

### Compilation layer

Builds a task-specific context graph, removes exact duplicate records context-locally, groups referents only when explicit upstream identity/equivalence supports it, surfaces conflicts, computes declared derived views, and applies context budgets. It never mints Kristall semantic identity. For v7 Surface operations it preserves the separation between source assertions, derived assertions, structural relations, similarity signals, hypotheses and paths.

### Output layer

Emits a stable Context Pack plus execution/provenance metadata.

## Isolation rule

A failure in one operation MUST NOT corrupt successful sibling outputs. Whether the overall run aborts, partially succeeds, or skips dependents is controlled by the Query Plan's declared error policy.


## v7 two-plane model

Kompiler 0.5 treats Kristal Standard v7 as two cooperating planes:

```text
source plane                         meta plane
-----------                          ----------
Kristal v6 state  ───────────────►   Kristall v7 manifest
state_id preserved                   KQ/KP/KA/KS registries
source assertions                    Mesh + families + axes
reader/view policy                   subject regions + recipes
        │                                      │
        └──────────────► Surface ◄─────────────┘
                              │
                              ▼
                       Context Pack 1.1
                              │
                    optional projection
                              ▼
                    kristal_state/6.0
                    + extensions.kristal_v7
```

The meta-plane may organize and derive views over source states, but it does not overwrite their state identity or grant execution authority.


## Ecosystem authority boundary

Kompiler reads Kristal/Kristall surfaces. Persistent source storage belongs to Médiathèque kOA; DaaT (`daat`) is an optional external IK↔Kristal mapping boundary; KQ/KP/KA/KS identity and crystallization remain Kristal/Kristall-owned. See [Ecosystem Boundaries](ecosystem-boundaries.md).
