"""Offline *consumer* pilot with genuine Zoology bytes; never creates a publication."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest

from kompiler.adapters.github_collection import GithubCollectionAdapter
from kompiler.config import AppConfig, StorageConfig
from kompiler.errors import AdapterError
from kompiler.github_collection import CollectionReader
from kompiler.protocol.canonical import canonical_bytes
from kompiler.protocol.models import QueryPlan
from kompiler.registry import AdapterRegistry
from kompiler.runtime import KompilerRuntime


def sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def make_private_zoology_fixture(zoology: Path, root: Path) -> Path:
    """A derived fake host wrapper, NOT a Manager release or a qualified/public artifact."""
    ai_doc = json.loads((zoology / "ai/INDEX.json").read_text())
    manifest = json.loads((zoology / "AI_MANIFEST.json").read_text())
    state = json.loads((zoology / "state/state-snapshot.json").read_text())
    assert ai_doc["state_ref"] == manifest["state_ref"] == state["state_ref"]
    assert ai_doc["state_logical_commitment"] == manifest["state_logical_commitment"] == state["logical_commitment"]
    slug = "zoology"
    base = root / "kristals" / slug
    files = set(["README.md", "AI_START_HERE.md", "AI_MANIFEST.json", "ai/INDEX.json"])
    files.update(str(r["path"]) for r in ai_doc["files"])
    files.update(str(p) for p in manifest["read_order"])
    files.update(f"ai/{p.name}" for p in (zoology / "ai").iterdir() if p.is_file())
    rows = []
    for rel in sorted(files, key=lambda p: p.encode("utf-8")):
        assert ".." not in rel.split("/")
        src = zoology / rel
        assert src.is_file(), rel
        dst = base / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        content = dst.read_bytes()
        assert content == src.read_bytes()
        role = next((r["role"] for r in ai_doc["files"] if r["path"] == rel), "supporting_content")
        rows.append({"path": rel, "role": role, "size": len(content), "sha256": sha(content)})
    objects = ai_doc.get("materialization_blobs") or []
    surface = {"format": "kristal.github-read-surface/1.0", "slug": slug,
               "state_ref": state["state_ref"], "state_logical_commitment": state["logical_commitment"],
               "entrypoint": "AI_START_HERE.md", "files": rows, "materialization_objects": objects}
    digest = sha(canonical_bytes(surface))
    sync = {"format": "kristal.github-sync-manifest/1.0", "read_surface_format": surface["format"],
            "target_root": "kristals/zoology", "slug": slug, "entrypoint": "AI_START_HERE.md",
            "state_ref": state["state_ref"], "state_logical_commitment": state["logical_commitment"],
            "surface_digest": digest, "files": rows, "file_count": len(rows),
            "total_bytes": sum(x["size"] for x in rows), "materialization_object_count": len(objects)}
    (base / ".kristal").mkdir(parents=True)
    (base / ".kristal/sync-manifest.json").write_text(json.dumps(sync), encoding="utf-8")
    entry = {"slug": slug, "title": "Kristal-Zoology", "path": "kristals/zoology",
             "entrypoint": "kristals/zoology/AI_START_HERE.md", "state_ref": state["state_ref"],
             "state_logical_commitment": state["logical_commitment"], "surface_digest": digest,
             "file_count": len(rows), "total_bytes": sync["total_bytes"],
             "materialization_object_count": len(objects)}
    index = {"format": "kristal.github-collection-index/1.0", "kristals": [entry]}
    idxbytes = json.dumps(index, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    index.update({"count": 1, "index_digest": sha(idxbytes)})
    (root / "kristals/index.json").write_text(json.dumps(index), encoding="utf-8")
    return root


@pytest.mark.asyncio
async def test_real_zoology_verifiable_private_surface_and_context_pack(tmp_path):
    root_raw = os.getenv("C5_ZOOLOGY_ROOT")
    if not root_raw:
        pytest.skip("set C5_ZOOLOGY_ROOT; first build-ai on a disposable copy")
    local = Path(root_raw)
    if not (local / "AI_MANIFEST.json").exists():
        pytest.skip("requires built AI layer in a disposable Zoology copy")
    fixture = make_private_zoology_fixture(local, tmp_path / "private-host")
    reader = CollectionReader(fixture)
    assert reader.catalog(query="zoology")["count"] == 1
    entry = reader.read("zoology", "AI_START_HERE.md")
    assert "zoology" in entry["slug"]
    assert entry["state_ref"] == "urn:kristal:state:kristal-zoology"
    assert reader.reading_map("zoology")["file_count"] > 10
    adapter = GithubCollectionAdapter(fixture)
    registry = AdapterRegistry()
    registry.register(adapter)
    runtime = KompilerRuntime(AppConfig(storage=StorageConfig(database=tmp_path / "c5.db", cache=False)), registry, None)
    query = QueryPlan.model_validate({"request_id": "zoology-verified-private-read", "topic": "zoology",
                                      "operations": [{"id": "intro", "target": adapter.target_id,
                                                      "operation": "entrypoint", "params": {"slug": "zoology"}}]})
    pack = await runtime.run(query)
    assert pack.protocol == "kompiler.context-pack"
    assert pack.summary.record_count == 1
    assert all(receipt.status == "success" for receipt in pack.execution.receipts)
    assert all(c.semantics.read_only and not c.semantics.network for c in adapter.capabilities())
    (fixture / "kristals/zoology/AI_START_HERE.md").write_text("tampered!", encoding="utf-8")
    with pytest.raises(AdapterError, match="DIGEST_MISMATCH"):
        reader.read("zoology", "AI_START_HERE.md")
    with pytest.raises(AdapterError, match="UNDECLARED_RESOURCE"):
        reader.read("zoology", "not-in-index.json")
