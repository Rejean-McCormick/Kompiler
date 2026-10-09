# Vision and Scope

## One-sentence definition

**Kompiler compiles structured knowledge from one or more Kristals into a task-specific Context Pack for an AI conversation or agent workflow.**

## The problem

Large language models reason well when the active context is strong, but constructing that context is often the expensive part. Traditional retrieval commonly returns a small collection of passages. Kompiler instead assembles a structured problem model: assertions, referents, relations, valuations, conflicts, provenance, gaps, and derived projections selected for the current task.

The canonical workflow is:

```text
human question
    ↓
LLM identifies information needs
    ↓
kompiler.query
    ↓
local Kompiler runtime
    ↓
Kristal adapters → Kristals
    ↓
adapter-output normalization + joins + compilation + budgeting
    ↓
kompiler.context-pack
    ↓
LLM reasoning for the rest of the conversation
```

## Goals

Kompiler MUST support:

- heavy, multi-operation, multi-Kristal query plans;
- local/offline execution where the underlying Kristals permit it;
- deterministic execution after a query plan has been accepted;
- capability discovery so an LLM does not guess available operations;
- explicit DAG dependencies between operations;
- preservation of Kristal epistemic metadata and provenance;
- bounded output sized for an LLM context window;
- multi-pass research where later queries fill gaps found in an earlier Context Pack;
- transport independence;
- explicit compatibility with heterogeneous existing Kristal query surfaces.

## Non-goals

Kompiler is not:

- a source crawler, acquisition pipeline, or canonical source store;
- a DaaT replacement or IK↔Kristal mapping authority;
- a Kristall semantic-identity/crystallization authority;
- a truth engine;
- an authority registry;
- a general-purpose shell executor;
- a replacement for Kristal validation;
- a mechanism for silently upgrading `claimed`, `sourced`, high-valued, or validated material into universal truth;
- a system that grants mutation permission based on `actionability`;
- a requirement that all Kristals use the same storage model;
- a requirement that the LLM itself be deterministic.

## Deterministic boundary

The LLM may produce different valid plans for the same natural-language prompt. **Kompiler's deterministic promise begins after an accepted Query Plan is fixed.** Given identical Kristal content, adapter versions, policies, configuration, and request bytes, deterministic operations SHOULD return byte-stable normalized outputs and stable ordering within their declared contract.
