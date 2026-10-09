from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def load_model(path: str | Path, model: type[T]) -> T:
    return model.model_validate(load_json(path))


def dump_json(value: Any, path: str | Path | None = None, *, pretty: bool = True) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(by_alias=True, mode="json", exclude_none=True)
    text = json.dumps(
        value,
        ensure_ascii=False,
        indent=2 if pretty else None,
        separators=None if pretty else (",", ":"),
    )
    if path is not None:
        Path(path).write_text(text + "\n", encoding="utf-8")
    return text
