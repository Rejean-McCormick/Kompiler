# Execution Engine

## Responsibilities

The executor runs an admitted DAG safely and predictably. It is responsible for scheduling, cancellation, deadlines, limits, dependency propagation, operation caching, and capturing adapter results.

## Planning

The planner computes:

- topological order and parallel stages;
- required upstream selectors;
- capability bindings;
- semantic Query Plan hash;
- capability-snapshot binding;
- read-only and network-policy admission.

## Parallelism

Independent read-only operations may execute concurrently. Parallel completion order does not control Context Pack ordering; normalization/compiler stages apply stable ordering before semantic hashing.

Request parallelism is clamped by the administrator runtime limit.

## Required and optional inputs

A failed required input causes the dependent operation to be skipped. An optional binding may resolve to an empty selection. Successful upstream operations are allowed to produce an empty required selection: emptiness is data, not an execution failure.

Every selector result is subject to the global `max_join_items` fan-in limit before it can be injected into a downstream operation.

## Resource limits

Each operation is constrained by the minimum of caller, capability, and runtime limits:

- wall-clock timeout;
- max normalized result items;
- max normalized result bytes;
- max subprocess stdout/stderr bytes;
- global join fan-in.

The executor applies item/byte bounding again after adapter execution so in-process and third-party adapters cannot bypass declared operation limits.

## Subprocess adapters

When an adapter uses an existing CLI:

- executable/script paths are trusted adapter implementation details;
- parameters are passed as an argument vector, never a shell string;
- `shell=True` is not used;
- cwd is explicit;
- environment is minimized/allowlisted;
- stdout/stderr are read incrementally with hard byte ceilings;
- timeout is mandatory;
- cancellation/timeout terminates the child process group best-effort;
- exit status is captured;
- JSON output is validated before normalization.

The subprocess capture ceiling is separate from the semantic operation result-byte budget. A CLI may emit formatted JSON larger than the final canonical bounded result without being incorrectly rejected, provided it remains under the administrator stdout limit.

## In-process adapters

Preferred where a stable structured corpus/library interface exists. Direct JSON adapters cache parsed documents while `mtime_ns` and file size are unchanged.

## Operation receipts

Receipts record operational metadata including timing, adapter/source identity, counts, truncation, cache hit, and error information. Timing and cache-hit fields are audit metadata and are excluded from Context Pack semantic identity.
