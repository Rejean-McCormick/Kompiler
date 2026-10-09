from __future__ import annotations

import abc
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kompiler.protocol.models import OperationCapability, SourceDescriptor, SurfaceSelector


@dataclass(slots=True)
class AdapterContext:
    operation_id: str
    reader_policy: str | None = None
    timeout_ms: int = 30_000
    max_items: int | None = None
    max_bytes: int | None = None
    max_stdout_bytes: int = 8_000_000
    upstream: dict[str, Any] = field(default_factory=dict)
    surface: SurfaceSelector | None = None


@dataclass(slots=True)
class AdapterResult:
    items: list[Any] = field(default_factory=list)
    referents: list[dict[str, Any]] = field(default_factory=list)
    relations: list[dict[str, Any]] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)
    derived: list[dict[str, Any]] = field(default_factory=list)
    subjects: list[dict[str, Any]] = field(default_factory=list)
    axes: list[dict[str, Any]] = field(default_factory=list)
    assertion_families: list[dict[str, Any]] = field(default_factory=list)
    resonance: list[dict[str, Any]] = field(default_factory=list)
    surfaces: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    raw_item_count: int = 0
    truncated: bool = False

    def __post_init__(self) -> None:
        if self.raw_item_count == 0:
            self.raw_item_count = len(self.items)


class Adapter(abc.ABC):
    adapter_id: str
    adapter_version: str = "1.0.0"
    target_id: str
    kind: str = "kristal"
    root: Path

    @abc.abstractmethod
    def capabilities(self) -> list[OperationCapability]:
        raise NotImplementedError

    @abc.abstractmethod
    async def execute(self, operation: str, params: dict[str, Any], context: AdapterContext) -> AdapterResult:
        raise NotImplementedError

    @abc.abstractmethod
    def source_descriptor(self) -> SourceDescriptor:
        raise NotImplementedError

    def health(self) -> dict[str, Any]:
        return {"ok": self.root.exists(), "root": str(self.root), "adapter_id": self.adapter_id}
