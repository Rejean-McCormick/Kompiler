from __future__ import annotations

from pathlib import Path
from typing import Iterable

from kompiler.adapters.base import Adapter
from kompiler.adapters.builtin import BUILTIN_FACTORIES, detect_builtin
from kompiler.adapters.manifest import AdapterManifest
from kompiler.errors import AdmissionError
from kompiler.protocol.canonical import prefixed_hash
from kompiler.protocol.models import (
    AdapterDescriptor,
    CapabilitySnapshot,
    RuntimeDescriptor,
    TargetCapability,
)
from kompiler.version import __version__


class AdapterRegistry:
    def __init__(self) -> None:
        self._by_target: dict[str, Adapter] = {}

    def register(self, adapter: Adapter) -> None:
        if adapter.target_id in self._by_target:
            raise ValueError(f"duplicate adapter target: {adapter.target_id}")
        self._by_target[adapter.target_id] = adapter

    def get(self, target_id: str) -> Adapter:
        try:
            return self._by_target[target_id]
        except KeyError as exc:
            raise AdmissionError("UNKNOWN_TARGET", f"Unknown target {target_id}", {"available_targets": self.targets}) from exc

    @property
    def targets(self) -> list[str]:
        return sorted(self._by_target)

    def adapters(self) -> list[Adapter]:
        return [self._by_target[k] for k in self.targets]

    def snapshot(self) -> CapabilitySnapshot:
        targets = [
            TargetCapability(
                target_id=a.target_id,
                kind=a.kind,
                adapter=AdapterDescriptor(id=a.adapter_id, version=a.adapter_version),
                source=a.source_descriptor(),
                operations=a.capabilities(),
            )
            for a in self.adapters()
        ]
        semantic = {
            "runtime": {"name": "kompiler", "version": __version__},
            "targets": [x.model_dump(mode="json", exclude_none=True) for x in targets],
        }
        return CapabilitySnapshot(
            snapshot_id=prefixed_hash("cap", semantic),
            runtime=RuntimeDescriptor(version=__version__),
            targets=targets,
        )

    @classmethod
    def from_manifests(cls, manifests: Iterable[str | Path]) -> "AdapterRegistry":
        reg = cls()
        for path in manifests:
            manifest = AdapterManifest.load(path)
            if manifest.adapter_type not in BUILTIN_FACTORIES:
                raise ValueError(f"unknown adapter implementation type {manifest.adapter_type!r}")
            reg.register(BUILTIN_FACTORIES[manifest.adapter_type](manifest))
        return reg


def discover(paths: Iterable[str | Path]) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    seen_targets: set[str] = set()
    skip_names = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache"}
    for base in paths:
        root = Path(base).expanduser().resolve()
        if not root.exists():
            continue
        queue: list[tuple[Path, int]] = [(root, 0)]
        visited: set[Path] = set()
        while queue:
            p, depth = queue.pop(0)
            try:
                p = p.resolve()
            except OSError:
                continue
            if p in visited:
                continue
            visited.add(p)
            hit = detect_builtin(p)
            if hit and (hit[0], str(hit[1])) not in seen:
                seen.add((hit[0], str(hit[1])))
                if hit[2] not in seen_targets:
                    seen_targets.add(hit[2])
                    found.append({"adapter_type": hit[0], "root": str(hit[1]), "target_id": hit[2]})
                # Once a Kristal root is recognized, descending inside it only produces
                # duplicate signatures and can be expensive for large corpora.
                if hit[1].resolve() == p and hit[0] != "kristall-v7":
                    continue
            if depth >= 5 or not p.is_dir():
                continue
            try:
                children = sorted(
                    (
                        child
                        for child in p.iterdir()
                        if child.is_dir()
                        and not child.is_symlink()
                        and child.name not in skip_names
                        and not child.name.startswith(".")
                    ),
                    key=lambda child: child.name.lower(),
                )
            except (OSError, PermissionError):
                continue
            queue.extend((child, depth + 1) for child in children)
    return found
