"""C5: immutable Framework pins and failure-closed semantic baseline selection."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from kompiler.errors import StandardError
from kompiler.kristal_standard import KristalStandard, configure_standard_root, standard_lock


def _framework(tmp_path: Path, version: str, content: bytes) -> Path:
    root = tmp_path / "framework"
    (root / "contracts").mkdir(parents=True)
    for v in ("v6", "v7", "v8", "v9", "v10"):
        (root / "schemas" / v).mkdir(parents=True)
    (root / "contracts" / "release.json").write_text(json.dumps({
        "version": version, "semantic_baseline": {"schema_root": "schemas/v7"},
    }), encoding="utf-8")
    (root / "contracts" / "contract-set.json").write_bytes(content)
    return root


def test_draft31_is_explicitly_pinned(monkeypatch, tmp_path):
    version = "10.0.0-draft.3.1"
    lock = standard_lock()
    expected = lock["additional_contract_set_pins"][version]
    assert len(expected) == 64
    assert version in lock["additional_supported_versions"]
    root = _framework(tmp_path, version, b'{}\n')
    monkeypatch.delenv("KOMPILER_KRISTAL_CONTRACT_SET_SHA256", raising=False)
    configure_standard_root(None)
    with pytest.raises(StandardError, match="MISMATCH"):
        KristalStandard.load(root)
    monkeypatch.setenv("KOMPILER_KRISTAL_CONTRACT_SET_SHA256", "0" * 64)
    with pytest.raises(StandardError, match="MISMATCH"):
        KristalStandard.load(root)
    valid_sha = hashlib.sha256(b'{}\n').hexdigest()
    monkeypatch.setenv("KOMPILER_KRISTAL_CONTRACT_SET_SHA256", valid_sha)
    assert KristalStandard.load(root).version == version
    monkeypatch.delenv("KOMPILER_KRISTAL_CONTRACT_SET_SHA256", raising=False)


def test_draft31_real_snapshot_pin_when_supplied(monkeypatch):
    import os
    raw = os.getenv("C5_FRAMEWORK_ROOT")
    if not raw:
        pytest.skip("set C5_FRAMEWORK_ROOT to run against the real Framework")
    monkeypatch.delenv("KOMPILER_KRISTAL_CONTRACT_SET_SHA256", raising=False)
    configure_standard_root(None)
    root = Path(raw)
    pin = standard_lock()["additional_contract_set_pins"]["10.0.0-draft.3.1"]
    assert hashlib.sha256((root / "contracts/contract-set.json").read_bytes()).hexdigest() == pin
    assert KristalStandard.load(root).version == "10.0.0-draft.3.1"
