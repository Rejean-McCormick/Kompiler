# Error Contract

All non-pack terminal failures use `kompiler.error/1.1`.

## Shape

```json
{
  "protocol": "kompiler.error",
  "version": "1.1",
  "request_id": "pollution-001",
  "generated_at": "2026-10-02T15:01:00Z",
  "error": {
    "code": "UNKNOWN_OPERATION",
    "message": "Target HumanBody does not expose operation toxicity.",
    "operation_id": "human_effects",
    "retryable": false,
    "details": {
      "available_operations": ["find", "mechanisms", "relations"]
    }
  }
}
```

## Stable v1 error codes

### Protocol/admission

- `UNSUPPORTED_PROTOCOL_VERSION`
- `INVALID_JSON`
- `SCHEMA_VIOLATION`
- `CAPABILITY_SNAPSHOT_MISMATCH`
- `UNKNOWN_TARGET`
- `UNKNOWN_OPERATION`
- `INVALID_PARAMETERS`
- `INVALID_DEPENDENCY`
- `CYCLIC_PLAN`
- `UNSUPPORTED_POLICY`

### Execution

- `ADAPTER_UNAVAILABLE`
- `ADAPTER_FAILURE`
- `ADAPTER_OUTPUT_INVALID`
- `TIMEOUT`
- `RESOURCE_LIMIT_EXCEEDED`
- `JOIN_CAP_EXCEEDED`
- `SOURCE_INTEGRITY_FAILURE`
- `SOURCE_NOT_FOUND`

### Compilation

- `NORMALIZATION_FAILURE`
- `UNSUPPORTED_VALUE_SEMANTICS`
- `BUDGET_IMPOSSIBLE`
- `COMPILATION_FAILURE`

### Security

- `FORBIDDEN_OPERATION`
- `PATH_OUTSIDE_ALLOWED_ROOT`
- `EXECUTABLE_NOT_ALLOWLISTED`
- `POLICY_DENIED`

## Determinism

For deterministic inputs and configuration, error classification and machine-readable details SHOULD also be deterministic. Stack traces are diagnostic data and MUST NOT appear in the protocol-facing `message` by default.
