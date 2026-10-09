# Protocol Overview

Kompiler v1 defines four primary message families.

| Protocol | Direction | Purpose |
|---|---|---|
| `kompiler.capabilities/1.1` | runtime → agent | Advertise targets, operations, schemas, policies, and limits |
| `kompiler.query/1.1` | agent → runtime | Declarative multi-operation query plan |
| `kompiler.context-pack/1.1` | runtime → agent | Compiled context plus execution/provenance metadata |
| `kompiler.error/1.1` | runtime → agent | Stable machine-readable failure |

## Common envelope

Every message MUST include:

```json
{
  "protocol": "kompiler.query",
  "version": "1.1"
}
```

Run-bound messages additionally include `request_id`. Runtime-produced messages include `generated_at` and SHOULD include a content hash.

## JSON rules

- Encoding: UTF-8.
- Duplicate object keys: invalid.
- Non-finite JSON numbers: invalid.
- Unknown top-level fields: rejected in strict mode; retained only if a future extension point explicitly permits them.
- Identifiers are case-sensitive unless a capability explicitly declares normalization.

## Extensions

Extensible objects use an optional `extensions` map. Extension keys SHOULD be globally namespaced, e.g. `org.example.feature`. Core behavior MUST NOT depend on an unknown extension.

## Hashing

When a protocol artifact declares `content_hash`, Kompiler canonicalizes the declared hash target with RFC 8785 JCS and hashes it with SHA-256. Identity/self-referential fields are excluded according to the artifact contract, not through local ad hoc rules.

## Forward compatibility

A v1 runtime MUST reject an unknown major version. It MAY accept a newer minor version only if the envelope declares compatibility and all required fields/semantics are understood.

## 1.0 compatibility

Protocol 1.1 is additive. Query, Context Pack, capability and error model parsers continue to accept version `1.0`; new v7 Surface and meta-plane fields require 1.1 semantics.
