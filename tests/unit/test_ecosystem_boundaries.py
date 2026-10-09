from pathlib import Path

from kompiler.adapters.builtin import BUILTIN_FACTORIES, detect_builtin
from kompiler.kristal_standard import standard_lock


def test_daat_and_authority_boundary_are_metadata_only():
    lock = standard_lock()
    notes = lock["boundary_notes"]
    assert lock["integration"] == "external-readonly"
    assert "not a Kompiler stage" in notes["daat"]
    assert "Mediatheque" in notes["source_authority"]
    assert "KQ/KP/KA/KS" in notes["semantic_authority"]


def test_raw_source_catalog_is_not_a_builtin_adapter(tmp_path: Path):
    catalog = tmp_path / "source-catalog"
    catalog.mkdir()
    (catalog / "providers.json").write_text("[]\n", encoding="utf-8")
    (catalog / "reference-sources.json").write_text("[]\n", encoding="utf-8")
    assert "kristal-foodbrands" not in BUILTIN_FACTORIES
    assert detect_builtin(tmp_path) is None
