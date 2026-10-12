"""C5: every verified hosted read retains exact state/provenance metadata.

These tests use the existing local fixture builder. They do not call GitHub,
change a canon, or qualify a real public collection.
"""
from __future__ import annotations

import base64
import json
import subprocess
from urllib.parse import unquote

from kompiler.adapters.github_collection import GithubCollectionAdapter
from kompiler.github_collection import CollectionReader
from tests.integration.test_github_collection import fixture_collection


def test_local_reader_preserves_distinct_commitment_and_surface_digest(tmp_path):
    root = fixture_collection(tmp_path)
    reader = CollectionReader(root)
    assert reader.catalog()["source_revision"] is None
    observed = reader.read("demo-0000", "AI_START_HERE.md")
    m = reader.manifest("demo-0000")
    assert observed["state_ref"] == m["state_ref"]
    assert observed["state_logical_commitment"] == m["state_logical_commitment"]
    assert observed["surface_digest"] == m["surface_digest"]
    assert observed["source_revision"] is None  # no invented Git commit for a local directory
    assert observed["state_logical_commitment"] != observed["surface_digest"]
    file_map = reader.reading_map("demo-0000")
    assert file_map["state_logical_commitment"] == m["state_logical_commitment"]
    assert file_map["source_revision"] is None
    health = GithubCollectionAdapter(root).health()
    assert health["source_revision"] is None


def test_remote_reader_exposes_the_exact_resolved_commit(tmp_path, monkeypatch):
    root = fixture_collection(tmp_path)
    revision = "b" * 40
    calls = []
    monkeypatch.setattr("kompiler.github_collection.shutil.which", lambda _: "/mock/gh")

    def fake_gh(command, **kwargs):
        endpoint = command[-1]
        calls.append(endpoint)
        if "/commits/" in endpoint:
            result = {"sha": revision}
        else:
            relative = unquote(endpoint.split("/contents/", 1)[1].split("?ref=", 1)[0])
            assert endpoint.endswith("?ref=" + revision)
            content = (root / relative).read_bytes()
            result = {
                "type": "file", "encoding": "base64", "size": len(content),
                "content": base64.b64encode(content).decode("ascii"),
            }
        return subprocess.CompletedProcess(command, 0, json.dumps(result), "")

    monkeypatch.setattr("kompiler.github_collection.subprocess.run", fake_gh)
    reader = CollectionReader("https://github.com/example/hosted-kristals")
    catalog = reader.catalog()
    assert catalog["source_revision"] == revision
    result = reader.read("demo-0000", "AI_START_HERE.md")
    m = reader.manifest("demo-0000")
    assert result["source_revision"] == revision
    assert result["state_logical_commitment"] == m["state_logical_commitment"]
    assert result["source"].endswith("/tree/" + revision)
    assert reader.reading_map("demo-0000")["source_revision"] == revision
    assert all(c.endswith("?ref=" + revision) for c in calls if "/contents/" in c)
