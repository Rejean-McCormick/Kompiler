# Transport Independence

The logical protocol is transport-agnostic.

## Supported/reference transports

### Clipboard

Human copies `kompiler.query` to the local app and returns `kompiler.context-pack` to the conversation. Lowest integration cost and easiest to audit.

### File

```text
inbox/query.json
outbox/context-pack.json
```

A watched folder MAY be supported, but auto-execution is opt-in.

### stdin/stdout

Ideal for scripts and agent runners.

### Local HTTP

Useful for desktop/web clients and future local integrations.

### MCP / agent connector

Future transport. It SHOULD expose protocol-native tools such as capabilities/validate/run rather than bypassing the runtime with arbitrary filesystem or shell access.

## Transport invariants

Changing transport MUST NOT change:

- target/operation semantics;
- validation behavior;
- reader/view policy;
- source identity;
- deterministic result ordering;
- error codes;
- Context Pack semantics.
