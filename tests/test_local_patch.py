"""Self-tests for safe local patch application; no real Kompiler checkout needed."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import subprocess
import sys


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/apply_update.py'
spec = importlib.util.spec_from_file_location('kompiler_patch_local', SCRIPT)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_preview_and_apply_to_source_anchor_fixture(tmp_path):
    (tmp_path / 'pyproject.toml').write_text('[project]\nname="kompiler"\n', encoding='utf8')
    original = {}
    for rel, changes in module.REPLACEMENTS.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        content = '\n'.join(old for old, _ in changes) + '\n'
        p.write_text(content, encoding='utf8')
        original[p] = content
    preview = subprocess.run([sys.executable, str(SCRIPT), str(tmp_path)], capture_output=True, text=True)
    assert preview.returncode == 0, preview.stderr
    assert 'PREVIEW ONLY' in preview.stdout
    for path, data in original.items():
        assert path.read_text(encoding='utf8') == data
    backup = tmp_path.parent / (tmp_path.name + '-backup')
    done = subprocess.run([sys.executable, str(SCRIPT), str(tmp_path), '--apply', '--backup-dir', str(backup)], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    for path, data in original.items():
        assert path.read_text(encoding='utf8') != data
        assert (backup / path.relative_to(tmp_path)).read_text(encoding='utf8') == data
    assert (tmp_path / 'tests/integration/test_v10_provenance_metadata.py').is_file()
    assert (tmp_path / 'docs/03-runtime/v10-alignment-update.md').is_file()


def test_rejects_mismatched_source_without_writing(tmp_path):
    (tmp_path / 'pyproject.toml').write_text('[project]\nname="kompiler"\n', encoding='utf8')
    (tmp_path / 'src/kompiler').mkdir(parents=True, exist_ok=True)
    file = tmp_path / 'src/kompiler/github_collection.py'
    file.write_text('# unrelated change\n', encoding='utf8')
    done = subprocess.run([sys.executable, str(SCRIPT), str(tmp_path), '--apply'], capture_output=True, text=True)
    assert done.returncode == 2
    assert 'BLOCKED' in done.stderr
    assert file.read_text() == '# unrelated change\n'
    assert not (tmp_path / 'tests/integration/test_v10_provenance_metadata.py').exists()
