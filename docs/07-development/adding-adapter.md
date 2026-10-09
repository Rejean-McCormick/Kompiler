# Adding a Kristal Adapter

## Checklist

1. Identify the Kristal's stable source root/artifact.
2. Identify its actual query mechanisms.
3. Define semantic operations useful to an agent.
4. Define strict input schemas.
5. Declare semantic dimensions and limitations.
6. Implement trusted native mappings.
7. Normalize outputs without epistemic upgrading.
8. Expose source identity/version.
9. Add adapter fixture(s).
10. Pass generic adapter conformance tests.
11. Document domain-specific semantics.

## Operation design

Prefer:

```text
progression
dependencies
mechanisms
relations
programs_by_prerequisite
```

Avoid exposing native implementation details as the public semantic API when a stable abstraction exists:

```text
run_query_py_with_argv
read_json_file_17
```

## When a generic `find` is acceptable

Use `find` when the underlying domain truly exposes generic filtering and the parameters themselves are well-described. Rich domain projections should get their own operation IDs when they carry non-obvious semantics.

## Native CLI mapping

For subprocess adapters:

```python
argv = [python_exe, query_script, "progression-grade", grade]
if discipline:
    argv.append(discipline)
```

Never interpolate into a shell command string.

## Output parser

Parsers MUST distinguish:

- valid empty result;
- native `not found` sentinel;
- malformed output;
- non-zero process failure;
- truncated output.

## Capability documentation

Each operation description should be understandable to an LLM without reading source code. Include parameter examples and semantic caveats, not implementation trivia.
