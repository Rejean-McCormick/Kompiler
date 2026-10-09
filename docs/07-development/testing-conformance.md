# Testing and Conformance

## Test layers

### Unit tests

Cover parsers, validators, selectors, DAG planning, normalization, ranking, hashing, and budget logic.

### Adapter contract tests

Every adapter runs against a fixture and proves:

- capability declaration matches behavior;
- valid parameters execute;
- invalid parameters fail before native execution;
- source IDs/provenance survive normalization;
- deterministic ordering is stable when declared;
- timeout/output caps are enforced.

### Integration tests

Exercise multi-adapter DAGs and Context Pack compilation.

### Property tests

Recommended properties:

- plan cycle detection is total;
- canonical hashing is stable under JSON object key order changes;
- exact dedupe is idempotent;
- applying the same budget policy twice is idempotent;
- normalized deterministic result order does not depend on parallel completion order.

### Golden vectors

Store canonical examples for:

- capabilities;
- valid/invalid queries;
- each stable error code;
- full and partial Context Packs;
- semantic hashes.

## Conformance suites

A runtime is protocol-conformant only if it passes the protocol vector suite. An adapter is target-conformant only if it passes the generic adapter suite plus its own domain fixtures.

## Kristal-specific tests

For v6 adapters, test preservation of:

- typed valuations/value states;
- record role;
- actionability;
- coordinates/applicability;
- source state identity behavior.

For v5 adapters, test preservation of:

- certainty;
- validation/authority metadata;
- reader-policy visibility;
- pagination/order/caps where exposed.

## Security tests

Mandatory cases include:

- shell metacharacters in string params;
- `../` path traversal;
- symlink escape;
- huge stdout;
- hanging subprocess;
- malformed JSON output;
- unknown capability injection;
- capability snapshot mismatch.
