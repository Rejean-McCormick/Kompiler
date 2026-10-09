# Coding Standards

## Python

- Python 3.12+.
- Type annotations for public APIs and protocol models.
- `from __future__ import annotations` where useful.
- No implicit global mutable registries in core modules.
- Use `pathlib.Path` for filesystem paths.
- Use timezone-aware UTC timestamps in runtime artifacts.
- No `shell=True`.
- Catch narrow exception types at boundaries; preserve root cause in internal diagnostics.

## Models

- Protocol models default to strict validation.
- Enums serialize to explicit stable strings.
- Unknown fields fail unless an extension point says otherwise.
- Every field with non-obvious semantics has documentation in schema/model metadata.

## JSON

- UTF-8.
- Stable deterministic serialization for hashing.
- Pretty formatting is presentation-only.

## Errors

- Internal exceptions are mapped once at the protocol boundary.
- Stable `error.code` values are never replaced with free-form exception names.

## Logging

- Structured event names.
- No secrets.
- No full source payload by default.

## Documentation

Any new public operation, protocol field, error code, hash rule, or semantic policy requires a documentation change in the same pull request.
