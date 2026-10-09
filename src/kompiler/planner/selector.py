from __future__ import annotations

import re
from typing import Any

from kompiler.errors import AdmissionError

_SEG = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")


def select(data: Any, expression: str) -> list[Any]:
    """Evaluate a deliberately tiny JSON selector grammar.

    Supported forms: `$`, `$.field`, `$.field[*]`, nested object fields, and array indices.
    Wildcards are only whole-array `[*]`; predicates/functions/scripts are forbidden.
    """
    if expression == "$":
        return [data]
    if not expression.startswith("$."):
        raise AdmissionError("INVALID_DEPENDENCY", f"unsupported selector {expression!r}")
    cursor: list[Any] = [data]
    rest = expression[2:]
    for raw in rest.split("."):
        wildcard = raw.endswith("[*]")
        index = None
        name = raw[:-3] if wildcard else raw
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\[(\d+)\]$", name)
        if m:
            name, index = m.group(1), int(m.group(2))
        elif not _SEG.match(name):
            raise AdmissionError("INVALID_DEPENDENCY", f"unsupported selector segment {raw!r}")
        nxt: list[Any] = []
        for item in cursor:
            if not isinstance(item, dict) or name not in item:
                continue
            value = item[name]
            if index is not None:
                if isinstance(value, list) and index < len(value): nxt.append(value[index])
            elif wildcard:
                if isinstance(value, list): nxt.extend(value)
            else:
                nxt.append(value)
        cursor = nxt
    return cursor
