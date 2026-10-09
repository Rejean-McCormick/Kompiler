from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class AdapterManifest:
    id: str
    version: str
    target_id: str
    kind: str
    root: Path
    adapter_type: str
    options: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path) -> "AdapterManifest":
        p = Path(path).expanduser().resolve()
        with p.open("rb") as f:
            d = tomllib.load(f)
        source = d.get("source", {})
        impl = d.get("implementation", {})
        root = Path(source.get("root", ".")).expanduser()
        if not root.is_absolute():
            root = (p.parent / root).resolve()
        return cls(
            id=d["id"],
            version=str(d.get("version", "1.0.0")),
            target_id=d["target_id"],
            kind=d.get("kind", "kristal"),
            root=root.resolve(),
            adapter_type=impl.get("type", d.get("adapter_type", "generic-json")),
            options={**d.get("execution", {}), **impl.get("options", {})},
        )
