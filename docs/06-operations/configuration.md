# Configuration

## Precedence

Reference precedence from lowest to highest:

```text
built-in defaults
→ system config
→ user config
→ project config
→ environment variables
→ CLI flags
→ request values bounded by admin limits
```

## Example `kompiler.toml`

```toml
[runtime]
max_parallelism = 4
default_timeout_ms = 30000
max_stdout_bytes = 8000000
max_join_items = 20000
strict_protocol = true
network_default = "deny"

[budgets]
max_items = 5000
max_bytes = 10000000
max_target_tokens = 250000

[storage]
database = "~/.local/share/kompiler/kompiler.db"
retention = "metadata"
cache = true

[logging]
level = "INFO"
format = "json"

[api]
enabled = true
host = "127.0.0.1"
port = 7788

[adapters.scolqc]
manifest = "~/.config/kompiler/adapters/scolqc.toml"
```

## Configuration hashing

Semantic configuration that can affect output MUST be included in the run's configuration hash. UI preferences and log formatting MUST NOT affect the semantic hash.

## Paths

All user-configurable paths are expanded and canonicalized before policy checks. Adapter roots SHOULD be absolute after resolution.

## Environment variables

Recommended prefix: `KOMPILER_`.

Examples:

```text
KOMPILER_LOG_LEVEL
KOMPILER_API_PORT
KOMPILER_DB_PATH
```

Secret-bearing variables MUST NOT be echoed into logs or Context Packs.

## Generated adapter configuration

`kompiler adapters bootstrap` writes manifests under `~/.config/kompiler/adapters/` by default and emits `~/.config/kompiler/adapters.generated.toml`. That generated fragment is part of the normal default configuration search path, after the main user config and before project config.

## Policy values

The reference runtime validates:

- `runtime.network_default`: `deny` or `allow`;
- `storage.retention`: `none`, `metadata`, `packs`, or `full`.

Capabilities declaring `semantics.network=true` are rejected at admission when the runtime policy is `deny`.
