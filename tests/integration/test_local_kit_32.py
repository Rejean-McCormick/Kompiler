import asyncio
import json
import os
from pathlib import Path

import pytest

from kompiler.adapters.base import AdapterContext
from kompiler.adapters.kristal_v9 import KristalV9StateAdapter

pytestmark = pytest.mark.skipif(
    not os.getenv("KOMPILER_KRISTAL_STANDARD_ROOT"),
    reason="Local Kit integration requires the external pinned Kristal Framework",
)


def test_local_kit_32_build_and_artifacts_are_readable(tmp_path: Path):
    framework = Path(os.environ["KOMPILER_KRISTAL_STANDARD_ROOT"]).resolve()
    workspace = tmp_path / "Local-Kristal"
    build = workspace / "build" / "v9"
    artifacts = build / "artifacts"
    artifacts.mkdir(parents=True)
    (workspace / "kristal.workspace.json").write_text(
        json.dumps({
            "format": "kristal.local-workspace/3.2.0",
            "slug": "local-kristal",
            "title": "Local Kristal",
        }),
        encoding="utf-8",
    )
    (build / "state-snapshot.json").write_bytes(
        (framework / "examples" / "v9" / "state-snapshot.example.json").read_bytes()
    )
    (artifacts / "example.logical-artifact.json").write_bytes(
        (framework / "examples" / "v9" / "logical-artifact.example.json").read_bytes()
    )

    adapter = KristalV9StateAdapter(workspace)
    health = adapter.health()
    assert health["ok"] is True
    assert health["local_surface"] == "build-v9"
    assert health["state_path"].endswith("build/v9/state-snapshot.json") or health["state_path"].endswith("build\\v9\\state-snapshot.json")

    source = adapter.source_descriptor()
    assert source.local_surface == "build-v9"
    assert source.workspace_format == "kristal.local-workspace/3.2.0"
    assert source.root_hint == "build/v9/state-snapshot.json"

    result = asyncio.run(adapter.execute("artifacts", {}, AdapterContext(operation_id="artifacts", max_items=100)))
    assert result.raw_item_count == 1
    assert result.items[0]["kind"] == "kristal_logical_artifact"
    assert "build/v9/artifacts/" in result.items[0]["source_file"]


def test_manager_catalog_auto_discovers_local_kit_workspace(tmp_path: Path):
    from kompiler.runtime import KompilerRuntime

    framework = Path(os.environ["KOMPILER_KRISTAL_STANDARD_ROOT"]).resolve()
    workspace = tmp_path / "Catalog-Kristal"
    build = workspace / "build" / "v9"
    build.mkdir(parents=True)
    (workspace / "kristal.workspace.json").write_text(
        json.dumps({
            "format": "kristal.local-workspace/3.2.0",
            "slug": "catalog-kristal",
            "title": "Catalog Kristal",
        }),
        encoding="utf-8",
    )
    (build / "state-snapshot.json").write_bytes(
        (framework / "examples" / "v9" / "state-snapshot.example.json").read_bytes()
    )
    catalog = tmp_path / "kristal-manager.json"
    catalog.write_text(json.dumps({
        "format": "kristal-local-registry/2.0",
        "entries": [{
            "path": str(workspace),
            "title": "Catalog Kristal",
            "backup_visibility": "private",
            "publication_target": "public",
        }],
    }), encoding="utf-8")
    config = tmp_path / "kompiler.toml"
    db = tmp_path / "kompiler.db"
    config.write_text(
        "\n".join([
            "[storage]",
            f'database = "{db.as_posix()}"',
            "[kristal_manager]",
            f'catalog = "{catalog.as_posix()}"',
            "auto_discover = true",
            "[kristal_standard]",
            f'root = "{framework.as_posix()}"',
        ]),
        encoding="utf-8",
    )

    rt = KompilerRuntime.create(config)
    try:
        assert any(target.startswith("KristalV9:") for target in rt.registry.targets)
        target = next(x for x in rt.capabilities().targets if x.target_id.startswith("KristalV9:"))
        assert target.source.local_surface == "build-v9"
        assert target.source.workspace_format == "kristal.local-workspace/3.2.0"
    finally:
        rt.close()
