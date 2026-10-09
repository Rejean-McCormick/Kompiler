from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EXCLUDE={"REPO_MANIFEST.json","uv.lock"}
EXCLUDE_PARTS={".git",".venv","__pycache__",".pytest_cache","node_modules","target","dist"}
rows=[]
for p in sorted(ROOT.rglob("*")):
    if not p.is_file(): continue
    rel=p.relative_to(ROOT)
    if rel.name in EXCLUDE or any(x in EXCLUDE_PARTS for x in rel.parts): continue
    if rel.suffix in {".db",".sqlite",".sqlite3",".pyc"}: continue
    b=p.read_bytes(); rows.append({"path":rel.as_posix(),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()})
out={"schema":"kompiler.repo-manifest/1.0","version":(ROOT/"VERSION").read_text().strip(),"file_count":len(rows),"files":rows}
(ROOT/"REPO_MANIFEST.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(f"wrote {len(rows)} entries")
