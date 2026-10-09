import json
from pathlib import Path

from kompiler.local_catalog import local_entries, load_local_catalog


def test_manager_catalog_is_inventory_only(tmp_path: Path):
    a = tmp_path / "A"
    b = tmp_path / "B"
    a.mkdir(); b.mkdir()
    catalog = tmp_path / "kristal-manager.json"
    catalog.write_text(json.dumps({
        "format": "kristal-local-registry/2.0",
        "entries": [
            {"path": str(b), "title": "Beta", "backup_visibility": "private", "publication_target": "none"},
            {"path": str(a), "title": "Alpha", "backup_visibility": "public", "publication_target": "public"},
        ],
    }), encoding="utf-8")
    loaded = load_local_catalog(catalog)
    rows = local_entries(catalog)
    assert loaded["format"] == "kristal-local-registry/2.0"
    assert [x["title"] for x in rows] == ["Alpha", "Beta"]
    assert rows[0]["backup_visibility"] == "public"
    assert rows[0]["publication_target"] == "public"
