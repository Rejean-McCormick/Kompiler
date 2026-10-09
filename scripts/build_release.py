from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
version = (ROOT / "VERSION").read_text().strip()

subprocess.run([sys.executable, str(ROOT / "scripts/check_contract_ownership.py")], check=True)
subprocess.run([sys.executable, str(ROOT / "scripts/export_schemas.py")], check=True)
subprocess.run([sys.executable, str(ROOT / "scripts/build_docs_manifest.py")], check=True)
subprocess.run([sys.executable, str(ROOT / "scripts/build_manifest.py")], check=True)

out = ROOT.parent / f"Kompiler-{version}-Windows.zip"
exclude = {".git", ".venv", "__pycache__", ".pytest_cache", "node_modules", "target", "dist"}
fixed_time = (1980, 1, 1, 0, 0, 0)

files: list[Path] = []
for p in ROOT.rglob("*"):
    if not p.is_file():
        continue
    rel = p.relative_to(ROOT)
    if any(x in exclude for x in rel.parts):
        continue
    if rel.suffix in {".db", ".sqlite", ".sqlite3", ".pyc"}:
        continue
    if rel.name.startswith((".cap-smoke", ".plan-smoke", ".pack-smoke")):
        continue
    files.append(p)

with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for p in sorted(files, key=lambda x: x.relative_to(ROOT).as_posix().encode("utf-8")):
        rel = p.relative_to(ROOT).as_posix()
        info = zipfile.ZipInfo(f"Kompiler-{version}/{rel}", date_time=fixed_time)
        info.compress_type = zipfile.ZIP_DEFLATED
        # Windows Explorer-compatible DOS metadata; reproducible timestamps.
        info.create_system = 0
        info.external_attr = 0x20
        z.writestr(info, p.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

print(out)
