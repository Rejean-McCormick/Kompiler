from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from kompiler.errors import AdmissionError

CATALOG_FORMATS = {"kristal-local-registry/2.0"}


def default_catalog_path() -> Path | None:
    """Best-effort operator catalog location. Never semantic authority."""
    env = os.getenv("KOMPILER_KRISTAL_MANAGER_CATALOG") or os.getenv("KRISTAL_MANAGER_CATALOG")
    if env:
        return Path(env).expanduser()
    if os.name == "nt":
        return Path(r"C:\mycode\Kristal\kristal-manager.json")
    candidate = Path.home() / "Kristal" / "kristal-manager.json"
    return candidate if candidate.exists() else None


def load_local_catalog(path: str | Path | None = None, *, required: bool = False) -> dict[str, Any]:
    p = Path(path).expanduser() if path else default_catalog_path()
    if p is None or not p.is_file():
        if required:
            raise AdmissionError("LOCAL_CATALOG_UNAVAILABLE", "Kristal Manager catalog is not available", {"path": str(p) if p else None})
        return {"format": "kristal-local-registry/2.0", "entries": [], "path": str(p) if p else None}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        raise AdmissionError("LOCAL_CATALOG_INVALID", f"Cannot read Kristal Manager catalog: {exc}", {"path": str(p)}) from exc
    if not isinstance(data, dict):
        raise AdmissionError("LOCAL_CATALOG_INVALID", "Kristal Manager catalog must be a JSON object", {"path": str(p)})
    fmt = str(data.get("format") or "")
    if fmt not in CATALOG_FORMATS:
        raise AdmissionError("LOCAL_CATALOG_UNSUPPORTED", f"Unsupported Kristal Manager catalog format: {fmt or 'missing'}", {"path": str(p)})
    entries = data.get("entries")
    if not isinstance(entries, list):
        raise AdmissionError("LOCAL_CATALOG_INVALID", "Kristal Manager catalog entries must be an array", {"path": str(p)})
    out = dict(data)
    out["path"] = str(p.resolve())
    return out


def local_entries(path: str | Path | None = None, *, existing_only: bool = True) -> list[dict[str, Any]]:
    data = load_local_catalog(path)
    rows: list[dict[str, Any]] = []
    for raw in data.get("entries", []):
        if not isinstance(raw, dict) or not raw.get("path"):
            continue
        p = Path(str(raw["path"])).expanduser()
        if existing_only and not p.exists():
            continue
        row = dict(raw)
        row["path"] = str(p.resolve()) if p.exists() else str(p)
        row["catalog_path"] = data.get("path")
        rows.append(row)
    return sorted(rows, key=lambda x: (str(x.get("title") or "").casefold(), str(x.get("path") or "").casefold()))


def discovery_paths(path: str | Path | None = None) -> list[Path]:
    return [Path(row["path"]) for row in local_entries(path) if row.get("path")]
