from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
forbidden_dirs = [
    ROOT / "schemas" / "kristal-v7",
    ROOT / "src" / "kompiler" / "kristall" / "schemas",
    ROOT / "vendor" / "kristal-standard-v7",
    ROOT / "examples" / "kristall-v7",
]
violations = [str(p.relative_to(ROOT)) for p in forbidden_dirs if p.exists()]
for p in ROOT.rglob("*.schema.json"):
    if p.name.startswith("kristall-") or p.name in {"kristal-state-v6.schema.json", "kristal-v7-extension.schema.json", "semantic-resonance.schema.json"}:
        violations.append(str(p.relative_to(ROOT)))
if violations:
    print("Kristal Standard ownership violation(s):")
    for item in sorted(set(violations)):
        print(" -", item)
    raise SystemExit(1)
print("contract ownership: PASS — no normative Kristal contracts vendored")
