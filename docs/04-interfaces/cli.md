# Command-Line Interface

The CLI is the simplest complete interface and the reference for automation.

## Core commands

```bash
kompiler capabilities
kompiler validate query.json
kompiler plan query.json
kompiler run query.json
kompiler run query.json --output context-pack.json
kompiler inspect context-pack.json
kompiler adapters list
kompiler adapters doctor
kompiler cache stats
kompiler cache clear
```

## Machine mode

`--json` makes stdout protocol-safe. Human progress/log output goes to stderr.

`kompiler validate` performs both protocol-model validation and runtime admission against the currently loaded capability snapshot; it does not execute operations.

```bash
kompiler capabilities --json > capabilities.json
kompiler run query.json --json > context-pack.json
```

## Clipboard workflow

The canonical zero-integration workflow is:

```text
1. `kompiler capabilities --json`
2. paste capabilities into ChatGPT
3. receive a kompiler.query JSON
4. save/drop JSON into Kompiler
5. `kompiler run query.json --json`
6. paste the Context Pack into ChatGPT
```

The desktop UI can automate steps 1, 4, and 5 without changing the protocol.

## Exit codes

Recommended stable classes:

- `0` success/context pack produced;
- `2` protocol/schema/admission error;
- `3` adapter/source error;
- `4` resource/timeout error;
- `5` compilation error;
- `6` security/policy denial;
- `130` user cancellation.

The full machine-readable error is written to stdout in `--json` mode or to the requested error artifact.

## Bootstrap and self-test

The reference implementation also exposes:

```bash
kompiler adapters discover /path/to/kristals
kompiler adapters bootstrap /path/to/kristals --output-dir ~/.config/kompiler/adapters
kompiler adapters manifest /path/to/one/kristal
kompiler self-test
```

`adapters bootstrap` performs signature discovery only, writes trusted manifest drafts, and emits a TOML config fragment. It does not execute scripts during discovery. `self-test` runs an isolated deterministic synthetic compilation through the same planner, executor, normalizer, compiler, and SQLite layers used by real runs.

The default generated bootstrap fragment is loaded automatically on subsequent commands.

## `project-v6`

Materialize one v7 Surface from a Context Pack as a v6-compatible `kristal_state`:

```bash
kompiler project-v6 context-pack.json \
  --surface-id surface:sha256:... \
  --recipe-id recipe:my-projection \
  -o projection.json
```

If the Context Pack contains exactly one Surface, `--surface-id` may be omitted. Structural Mesh edges, similarity signals and paths are not silently converted into assertions.
