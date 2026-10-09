"""Regression tests for untrusted, derived GitHub read surfaces."""
from __future__ import annotations

import base64
import json
import subprocess

import pytest

from kompiler.errors import AdapterError
from kompiler.github_collection import CollectionReader
from tests.integration.test_github_collection import fixture_collection


def test_cached_local_read_must_not_hide_later_tampering(tmp_path):
    root = fixture_collection(tmp_path)
    reader = CollectionReader(root)
    first = reader.read("demo-0000", "AI_START_HERE.md")
    assert "AI Entry" in first["content"]
    (root / "kristals/demo-0000/AI_START_HERE.md").write_text("tampered\n", encoding="utf-8")
    with pytest.raises(AdapterError, match="DIGEST_MISMATCH"):
        reader.read("demo-0000", "AI_START_HERE.md")


def test_spoofed_slug_and_missing_role_are_clean_errors(tmp_path):
    root = fixture_collection(tmp_path)
    manifest_file = root / "kristals/demo-0000/.kristal/sync-manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    manifest["slug"] = "other"
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(AdapterError, match="INTEGRITY_FAILURE"):
        CollectionReader(root).manifest("demo-0000")
    manifest["slug"] = "demo-0000"
    del manifest["files"][0]["role"]
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(AdapterError, match="INVALID_SOURCE"):
        CollectionReader(root).manifest("demo-0000")


def test_reject_control_characters_in_paths(tmp_path):
    reader = CollectionReader(fixture_collection(tmp_path))
    for path in ("AI_START_HERE.md\x00", "ai/INDEX.json\n", "ai/INDEX.json\x7f"):
        with pytest.raises(AdapterError, match="INVALID_PATH"):
            reader.read("demo-0000", path)


def test_remote_rejects_invalid_base64_and_false_size(tmp_path, monkeypatch):
    root = fixture_collection(tmp_path)
    monkeypatch.setattr("kompiler.github_collection.shutil.which", lambda _: "/fake/gh")
    response_mode = {"bad_encoding": True, "wrong_size": False}

    def mock_run(cmd, **kwargs):
        endpoint = cmd[-1]
        if "/commits/" in endpoint:
            document = {"sha": "e" * 40}
        else:
            from urllib.parse import unquote
            relative = unquote(endpoint.split("/contents/", 1)[1].split("?ref=", 1)[0])
            raw = (root / relative).read_bytes()
            document = {
                "type": "file", "encoding": "base64", "size": len(raw),
                "content": base64.b64encode(raw).decode(),
            }
            if relative.endswith("AI_START_HERE.md"):
                if response_mode["bad_encoding"]:
                    document["content"] += "###"
                elif response_mode["wrong_size"]:
                    document["size"] += 1
        return subprocess.CompletedProcess(cmd, 0, json.dumps(document), "")

    monkeypatch.setattr("kompiler.github_collection.subprocess.run", mock_run)
    reader = CollectionReader("https://github.com/acme/collection")
    with pytest.raises(AdapterError, match="INVALID_SOURCE"):
        reader.read("demo-0000", "AI_START_HERE.md")
    response_mode.update(bad_encoding=False, wrong_size=True)
    with pytest.raises(AdapterError, match="INTEGRITY_FAILURE"):
        reader.read("demo-0000", "AI_START_HERE.md")
