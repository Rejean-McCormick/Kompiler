# Local HTTP API

The local API is an optional transport over the same protocol models.

## Binding

Default binding SHOULD be loopback only:

```text
127.0.0.1:7788
```

Remote binding is disabled unless explicitly configured.

## Endpoints

### `GET /v1/capabilities`

Returns `kompiler.capabilities/1.1`.

### `POST /v1/queries/validate`

Validates a Query Plan without executing it.

### `POST /v1/runs`

Body: `kompiler.query/1.1`.

Synchronous mode returns a Context Pack/error when the configured request bounds allow it. The desktop app MAY use a run ID + polling/event stream for long local runs, but the wire artifacts remain the same.

### `GET /v1/runs/{run_id}`

Returns run state and receipts.

### `GET /v1/runs/{run_id}/context-pack`

Returns the final Context Pack when available.

With `storage.retention=metadata` or `none`, completed packs are not durable across process restarts. `packs` and `full` retention store the concrete artifact by `artifact_hash`; run history keeps both semantic `context_pack_id` and concrete `artifact_id`.

### `POST /v1/runs/{run_id}/cancel`

Requests cancellation.

Cancellation propagates to the executor and active subprocess groups. Async task handles are removed after completion so long-running operator sessions do not accumulate finished task objects.

## Error status mapping

The reference API uses transport status codes without changing the protocol error artifact:

- `422` for invalid/admission-rejected Query Plans;
- `403` for policy rejection;
- `413` when the requested total Context Pack budget is too small even for mandatory metadata (`BUDGET_IMPOSSIBLE`);
- `500` for unexpected compilation/runtime failures.

The JSON body remains `kompiler.error/1.1` so clients SHOULD branch on the protocol error `code`, not only on HTTP status.

## Authentication

Loopback-only single-user mode MAY use an ephemeral local bearer token shared with the desktop client. Any non-loopback binding MUST require explicit authentication and origin controls.

## CORS

Disabled by default. Desktop/web clients explicitly configure allowed origins.

## API is not a new semantic layer

The API MUST call the same admission, planner, executor, compiler, and schema code as the CLI. No endpoint-specific query semantics are allowed.

## `POST /v1/projections/v6`

Materializes a v7 Surface from an existing Context Pack as a v6-compatible `kristal_state`.

```json
{
  "context_pack": {},
  "surface_id": "surface:sha256:...",
  "recipe_id": "recipe:kompiler-adhoc"
}
```

`surface_id` is optional only when the pack contains exactly one Surface.
