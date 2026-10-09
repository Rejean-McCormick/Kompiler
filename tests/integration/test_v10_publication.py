import os
import shutil
import subprocess
from pathlib import Path

import pytest

from kompiler.adapters.kristal_v10 import KristalV10PublicationAdapter, find_v10_publication

pytestmark = pytest.mark.skipif(
    not os.getenv("KOMPILER_KRISTAL_STANDARD_ROOT") or not shutil.which("node"),
    reason="v10 publication integration requires external Kristal Framework and node",
)


def test_v10_publication_bundle_reader(tmp_path: Path):
    root = Path(os.environ["KOMPILER_KRISTAL_STANDARD_ROOT"]).resolve()
    cli = root / "reference/js/bin/kristal-ref.mjs"
    out = tmp_path / "bundle"
    subprocess.run([
        "node", str(cli), "build-publication-bundle-v10",
        str(root / "examples/v9/state-snapshot.example.json"),
        str(root / "examples/v10/node-manifest.example.json"),
        str(root / "examples/v10/github-binding.example.json"),
        str(out), "--source-commit", "1" * 40,
    ], check=True, capture_output=True, text=True)

    assert find_v10_publication(out) == out.resolve()
    adapter = KristalV10PublicationAdapter(out)
    health = adapter.health()
    assert health["ok"] is True
    assert health["publication_id"].startswith("urn:kristal:publication:sha256:")
    assert adapter.source_descriptor().integrity == "verified-v10-publication-bundle"
    assert {c.operation_id for c in adapter.capabilities()} == {"publication", "state"}
