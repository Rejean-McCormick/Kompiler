import hashlib
from pathlib import Path

import pytest

from kompiler.errors import StandardError
from kompiler.kristal_standard import configure_standard_root, get_standard, standard_lock


def test_standard_lock_is_metadata_only():
    lock = standard_lock()
    assert lock["integration"] == "external-readonly"
    assert lock["portable_contract"] == "kristal_state/6.0"
    assert lock["version"] == "10.0.0-draft.2"
    assert lock["lock_strength"] == "exact-contract-set-pin"
    assert lock["contract_set_sha256"] == "929166240f65c25e4feb6d0346f69b9122d0df861365ec40128337a6462a2ad0"
    assert lock["framework_commit"] == "27c0c7db3d79a4597c1c964fe8281fa35b5f858a"


def test_missing_standard_fails_closed(monkeypatch):
    monkeypatch.delenv("KOMPILER_KRISTAL_STANDARD_ROOT", raising=False)
    configure_standard_root(None)
    with pytest.raises(StandardError) as exc:
        get_standard()
    assert exc.value.code == "KRISTAL_STANDARD_UNAVAILABLE"


def test_no_normative_kristal_contracts_are_vendored():
    root = Path(__file__).resolve().parents[2]
    forbidden_dirs = [
        root / "schemas" / "kristal-v7",
        root / "src" / "kompiler" / "kristall" / "schemas",
        root / "vendor" / "kristal-standard-v7",
        root / "examples" / "kristall-v7",
    ]
    assert not any(p.exists() for p in forbidden_dirs)
    forbidden_names = {
        "kristal-state-v6.schema.json",
        "kristal-v7-extension.schema.json",
        "semantic-resonance.schema.json",
    }
    forbidden = [p for p in root.rglob("*.schema.json") if p.name in forbidden_names or p.name.startswith("kristall-")]
    assert forbidden == []
