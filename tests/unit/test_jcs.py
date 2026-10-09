from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from kompiler.protocol.canonical import canonical_bytes

ROOT = Path(__file__).resolve().parents[2]
VECTORS = ROOT / "tests" / "fixtures" / "kristal-jcs" / "vectors.json"


def _remove_top_level_pointers(value: dict, pointers: list[str]) -> dict:
    out = deepcopy(value)
    for pointer in pointers:
        assert pointer.startswith("/") and "/" not in pointer[1:], pointer
        out.pop(pointer[1:], None)
    return out


def test_kristal_rfc8785_golden_vectors():
    vectors = json.loads(VECTORS.read_text(encoding="utf-8"))["vectors"]
    for vector in vectors:
        value = _remove_top_level_pointers(
            vector["input"], vector.get("content_boundary", {}).get("exclude_json_pointers", [])
        )
        encoded = canonical_bytes(value)
        assert encoded.decode("utf-8") == vector["expected_canonical"], vector["id"]
        assert hashlib.sha256(encoded).hexdigest() == vector["expected_sha256_hex"], vector["id"]


def test_jcs_rejects_non_finite_numbers():
    with pytest.raises(ValueError):
        canonical_bytes({"x": float("nan")})
    with pytest.raises(ValueError):
        canonical_bytes({"x": float("inf")})


def test_jcs_rejects_unsafe_python_integers():
    with pytest.raises(ValueError):
        canonical_bytes({"x": 9007199254740992})
