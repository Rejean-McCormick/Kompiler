# Observability

## Correlation IDs

Every run has a `run_id`. Every operation has its Query Plan `operation_id`. Logs and receipts include both.

## Structured events

Recommended events:

```text
run.admitted
run.rejected
plan.compiled
operation.started
operation.cache_hit
operation.completed
operation.failed
operation.truncated
compiler.started
compiler.completed
budget.applied
pack.emitted
run.cancelled
```

## Metrics

Local metrics SHOULD include:

- run count by status;
- operation count by adapter/status;
- p50/p95 duration;
- cache hit ratio;
- raw vs normalized item count;
- records removed by exact dedupe;
- records removed by budget;
- conflict/gap counts;
- adapter health failures;
- source identity failures.

## Logging policy

Default logs SHOULD NOT contain full record payloads. Prefer IDs, counts, hashes, and bounded error summaries. Debug payload logging is opt-in because Kristals may contain sensitive data.

## Diagnostics bundle

`kompiler doctor --bundle` MAY create a redacted diagnostics archive containing:

- runtime version;
- OS/Python version;
- installed adapters and versions;
- capability snapshot metadata;
- recent error codes;
- config with secrets removed;
- selected run receipts without source payloads.
