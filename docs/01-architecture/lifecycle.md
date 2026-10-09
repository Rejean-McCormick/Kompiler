# Request Lifecycle

## 1. Capability snapshot

The caller obtains a `kompiler.capabilities` document. The snapshot has an identity/hash and describes exact operations and limits available for the run environment.

## 2. Query creation

An LLM or human produces a `kompiler.query` that references the capability snapshot or a compatible registry version.

## 3. Admission

Kompiler validates:

1. envelope/protocol version;
2. schema;
3. target existence;
4. operation existence;
5. parameter schema;
6. policy compatibility;
7. DAG references and acyclicity;
8. configured limits;
9. adapter health/availability when required;
10. v7 Surface requirements for meta-plane operations, including declared subject and primary orientation.

No operation begins before plan-level admission succeeds.

## 4. Planning

Dependencies are topologically sorted. Independent nodes form execution stages. Each node receives an immutable operation context containing run ID, resolved capability version, budgets, policy, and upstream inputs.

## 5. Execution

Adapters execute their trusted implementation. Raw outputs are captured with bounded stdout/stderr or structured in-process results. Kristall v7 adapters resolve the declared subject/orientation against validated registries and Mesh structure; they fail closed when an orientation cannot be bound to real structure.

## 6. Normalization

Adapter outputs are mapped to the Kompiler internal record model. Source payload fragments MAY be retained by reference or inline according to budget/configuration. v7 meta-objects are normalized into dedicated subject/axis/family/resonance/Surface collections rather than being promoted into source assertions.

## 7. Compilation

The compiler merges compatible records, builds relation indexes, exposes conflicts, records gaps, applies deterministic derivations, and produces a candidate context set.

## 8. Budgeting

Candidates are selected under the requested item/byte/token-estimate limits while preserving critical provenance and epistemic labels.

## 9. Finalization

Kompiler emits either:

- `kompiler.context-pack` with `status=success`, `partial`, or `empty`; or
- `kompiler.error` when no usable pack can be produced.

## 10. Conversation continuation

The Context Pack is passed to the LLM. The LLM may continue reasoning or emit another Query Plan targeting specific gaps. The second plan is a new run and MAY reference the previous pack ID for lineage.


## Optional portable projection

When a Context Pack contains exactly one selected v7 Surface (or a caller names one), Kompiler may materialize a portable `kristal_state/6.0` projection. The v7 lineage is written under `extensions.kristal_v7`; source v6 `state_id` values remain the projection inputs. This is a materialization boundary, not a conversion of the source Kristals into a new identity space.
