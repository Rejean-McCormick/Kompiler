from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
rows = []
for path in sorted(DOCS.rglob("*.md")):
    body = path.read_bytes()
    rows.append(
        {
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(body).hexdigest(),
            "bytes": len(body),
        }
    )
out = {"schema": "kompiler.docs-manifest/1.0", "count": len(rows), "files": rows}
(ROOT / "docs-manifest.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(f"wrote {len(rows)} documentation entries")
