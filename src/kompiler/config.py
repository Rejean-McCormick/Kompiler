from __future__ import annotations

import os
import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .protocol.canonical import prefixed_hash
from .kristal_standard import standard_lock


@dataclass(slots=True)
class RuntimeLimits:
    max_parallelism: int = 4
    default_timeout_ms: int = 30_000
    max_items: int = 5_000
    max_bytes: int = 10_000_000
    max_target_tokens: int = 250_000
    max_stdout_bytes: int = 8_000_000
    max_join_items: int = 20_000

    def __post_init__(self) -> None:
        for name in (
            "max_parallelism",
            "default_timeout_ms",
            "max_items",
            "max_bytes",
            "max_target_tokens",
            "max_stdout_bytes",
            "max_join_items",
        ):
            if getattr(self, name) < 1:
                raise ValueError(f"runtime limit {name} must be >= 1")


@dataclass(slots=True)
class StorageConfig:
    database: Path = Path.home() / ".local/share/kompiler/kompiler.db"
    cache: bool = True
    retention: str = "metadata"


@dataclass(slots=True)
class ApiConfig:
    enabled: bool = True
    host: str = "127.0.0.1"
    port: int = 7788
    bearer_token: str | None = None
    cors_origins: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.host:
            raise ValueError("api.host must not be empty")
        if not (1 <= self.port <= 65535):
            raise ValueError("api.port must be between 1 and 65535")


@dataclass(slots=True)
class StandardConfig:
    root: Path | None = None
    contract_set_sha256: str | None = None


@dataclass(slots=True)
class ManagerConfig:
    catalog: Path | None = None
    auto_discover: bool = False


@dataclass(slots=True)
class AppConfig:
    strict_protocol: bool = True
    network_default: str = "deny"
    limits: RuntimeLimits = field(default_factory=RuntimeLimits)
    storage: StorageConfig = field(default_factory=StorageConfig)
    api: ApiConfig = field(default_factory=ApiConfig)
    standard: StandardConfig = field(default_factory=StandardConfig)
    manager: ManagerConfig = field(default_factory=ManagerConfig)
    github_collections: list[str] = field(default_factory=list)
    adapter_manifests: list[Path] = field(default_factory=list)
    log_level: str = "INFO"
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def semantic_hash(self) -> str:
        semantic = {
            "strict_protocol": self.strict_protocol,
            "network_default": self.network_default,
            "limits": asdict(self.limits),
            "adapter_manifests": sorted(str(p) for p in self.adapter_manifests),
            "kristal_standard": {"base_version": standard_lock()["version"], "contract_set_sha256": self.standard.contract_set_sha256 or standard_lock()["contract_set_sha256"], "framework_commit": standard_lock().get("framework_commit") if not self.standard.contract_set_sha256 else None},
            "kristal_manager": {"auto_discover": self.manager.auto_discover},
            "github_collections": sorted(self.github_collections),
        }
        return prefixed_hash("cfg", semantic)


def _merge(dst: dict[str, Any], src: dict[str, Any]) -> dict[str, Any]:
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _merge(dst[k], v)
        else:
            dst[k] = v
    return dst


def _load_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("rb") as f:
        return tomllib.load(f)


def default_config_paths() -> list[Path]:
    paths = [Path("/etc/kompiler/kompiler.toml")]
    paths.append(Path.home() / ".config/kompiler/kompiler.toml")
    # `kompiler adapters bootstrap` writes this fragment by default. Loading it
    # automatically makes bootstrap an actual configure-and-run workflow.
    paths.append(Path.home() / ".config/kompiler/adapters.generated.toml")
    project = Path.cwd() / "kompiler.toml"
    paths.append(project)
    return paths


def load_config(extra_path: str | Path | None = None) -> AppConfig:
    data: dict[str, Any] = {}
    if extra_path is None and os.getenv("KOMPILER_CONFIG"):
        extra_path = os.environ["KOMPILER_CONFIG"]
    for path in default_config_paths():
        _merge(data, _load_toml(path))
    if extra_path:
        _merge(data, _load_toml(Path(extra_path).expanduser()))

    runtime = data.get("runtime", {})
    budgets = data.get("budgets", {})
    storage = data.get("storage", {})
    api = data.get("api", {})
    logging_cfg = data.get("logging", {})
    standard_cfg = data.get("kristal_standard", {})
    manager_cfg = data.get("kristal_manager", {})
    github_cfg = data.get("github", {})

    limits = RuntimeLimits(
        max_parallelism=int(os.getenv("KOMPILER_MAX_PARALLELISM", runtime.get("max_parallelism", 4))),
        default_timeout_ms=int(runtime.get("default_timeout_ms", 30_000)),
        max_items=int(budgets.get("max_items", 5_000)),
        max_bytes=int(budgets.get("max_bytes", 10_000_000)),
        max_target_tokens=int(budgets.get("max_target_tokens", 250_000)),
        max_stdout_bytes=int(runtime.get("max_stdout_bytes", 8_000_000)),
        max_join_items=int(runtime.get("max_join_items", 20_000)),
    )
    db = Path(os.getenv("KOMPILER_DB_PATH", storage.get("database", "~/.local/share/kompiler/kompiler.db"))).expanduser()
    app = ApiConfig(
        enabled=bool(api.get("enabled", True)),
        host=str(api.get("host", "127.0.0.1")),
        port=int(os.getenv("KOMPILER_API_PORT", api.get("port", 7788))),
        bearer_token=os.getenv("KOMPILER_API_TOKEN", api.get("bearer_token")),
        cors_origins=[str(x) for x in api.get("cors_origins", [])],
    )
    manifests: list[Path] = []
    for _, desc in data.get("adapters", {}).items():
        if isinstance(desc, dict) and desc.get("manifest"):
            manifests.append(Path(desc["manifest"]).expanduser())
    env_manifests = os.getenv("KOMPILER_ADAPTER_MANIFESTS")
    if env_manifests:
        manifests.extend(Path(x).expanduser() for x in env_manifests.split(os.pathsep) if x)
    network_default=str(runtime.get("network_default", "deny"))
    if network_default not in {"deny", "allow"}:
        raise ValueError("runtime.network_default must be 'deny' or 'allow'")
    retention=str(storage.get("retention", "metadata"))
    if retention not in {"none", "metadata", "packs", "full"}:
        raise ValueError("storage.retention must be one of: none, metadata, packs, full")
    return AppConfig(
        strict_protocol=bool(runtime.get("strict_protocol", True)),
        network_default=network_default,
        limits=limits,
        storage=StorageConfig(database=db, cache=bool(storage.get("cache", True)), retention=retention),
        api=app,
        standard=StandardConfig(
            root=Path(os.getenv("KOMPILER_KRISTAL_STANDARD_ROOT", standard_cfg.get("root"))).expanduser() if (os.getenv("KOMPILER_KRISTAL_STANDARD_ROOT") or standard_cfg.get("root")) else None,
            contract_set_sha256=os.getenv("KOMPILER_KRISTAL_CONTRACT_SET_SHA256") or standard_cfg.get("contract_set_sha256"),
        ),
        manager=ManagerConfig(
            catalog=Path(os.getenv("KOMPILER_KRISTAL_MANAGER_CATALOG", manager_cfg.get("catalog"))).expanduser() if (os.getenv("KOMPILER_KRISTAL_MANAGER_CATALOG") or manager_cfg.get("catalog")) else None,
            auto_discover=bool(manager_cfg.get("auto_discover", False)),
        ),
        github_collections=[str(x) for x in github_cfg.get("collections", [])] + [x.strip() for x in os.getenv("KOMPILER_GITHUB_COLLECTIONS", "").split(";") if x.strip()],
        adapter_manifests=manifests,
        log_level=str(os.getenv("KOMPILER_LOG_LEVEL", logging_cfg.get("level", "INFO"))),
        raw=data,
    )
