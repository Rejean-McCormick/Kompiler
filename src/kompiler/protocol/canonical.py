from __future__ import annotations

import hashlib
import json
import math
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

_SAFE_INTEGER_MAX = 9007199254740991  # IEEE-754 / ECMAScript safe integer boundary.


def _default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "model_dump"):
        return value.model_dump(by_alias=True, mode="json", exclude_none=True)
    raise TypeError(f"Unsupported canonical JSON value: {type(value)!r}")


def _normalize(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    if isinstance(value, tuple):
        return [_normalize(v) for v in value]
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("Canonical JSON object keys must be strings")
            out[key] = _normalize(item)
        return out
    return _normalize(_default(value))


def _utf16_sort_key(value: str) -> bytes:
    # RFC 8785 sorts object property names by UTF-16 code units, not Unicode code points.
    return value.encode("utf-16-be", errors="strict")


def _json_string(value: str) -> str:
    # Python's JSON string escaping with ensure_ascii=False matches the JCS string rules:
    # preserve Unicode, escape control characters, quote and backslash, and do not escape '/'.
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _decompose_decimal(text: str) -> tuple[str, str, int]:
    """Return (sign, significant digits, decimal-point position) from Python repr text."""
    sign = ""
    if text.startswith("-"):
        sign, text = "-", text[1:]
    if "e" in text.lower():
        mantissa, exponent_text = text.lower().split("e", 1)
        exponent = int(exponent_text)
    else:
        mantissa, exponent = text, 0
    if "." in mantissa:
        left, right = mantissa.split(".", 1)
    else:
        left, right = mantissa, ""
    digits = (left + right).lstrip("0") or "0"
    # Decimal position counted from the first significant digit. Account for leading zeroes
    # in values such as 0.00123 by deriving from the original integer-part length.
    raw_digits = left + right
    first_nonzero = next((i for i, ch in enumerate(raw_digits) if ch != "0"), len(raw_digits) - 1)
    decimal_pos = len(left) + exponent - first_nonzero
    return sign, digits, decimal_pos


def _format_float(value: float) -> str:
    if not math.isfinite(value):
        raise ValueError("RFC 8785 forbids NaN and Infinity")
    if value == 0:
        return "0"

    # CPython repr already computes a shortest round-tripping decimal for IEEE-754 binary64.
    # JCS/ECMAScript differs primarily in notation thresholds and exponent spelling; normalize
    # those deterministically below.
    text = repr(value).lower()
    sign, digits, decimal_pos = _decompose_decimal(text)
    digits = digits.rstrip("0") or "0"
    abs_value = abs(value)

    # ECMAScript Number::toString uses fixed notation for [1e-6, 1e21).
    if 1e-6 <= abs_value < 1e21:
        if decimal_pos <= 0:
            body = "0." + ("0" * (-decimal_pos)) + digits
        elif decimal_pos >= len(digits):
            body = digits + ("0" * (decimal_pos - len(digits)))
        else:
            body = digits[:decimal_pos] + "." + digits[decimal_pos:]
        return sign + body

    # Scientific notation: exactly one leading digit; exponent has no leading zeroes and
    # includes '+' for non-negative exponents, matching ECMAScript/JCS.
    exponent = decimal_pos - 1
    mantissa = digits[0]
    if len(digits) > 1:
        mantissa += "." + digits[1:]
    exp = f"+{exponent}" if exponent >= 0 else str(exponent)
    return f"{sign}{mantissa}e{exp}"


def _serialize_jcs(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        if abs(value) > _SAFE_INTEGER_MAX:
            raise ValueError("Integer exceeds RFC 8785 / IEEE-754 safe integer domain")
        return str(value)
    if isinstance(value, float):
        return _format_float(value)
    if isinstance(value, str):
        return _json_string(value)
    if isinstance(value, list):
        return "[" + ",".join(_serialize_jcs(v) for v in value) + "]"
    if isinstance(value, dict):
        items = []
        for key in sorted(value, key=_utf16_sort_key):
            items.append(_json_string(key) + ":" + _serialize_jcs(value[key]))
        return "{" + ",".join(items) + "}"
    raise TypeError(f"Unsupported canonical JSON value after normalization: {type(value)!r}")


def canonical_bytes(value: Any) -> bytes:
    """RFC 8785 / JCS canonical JSON bytes.

    If the audited `rfc8785` package is available it is used directly. The built-in
    implementation exists so the local runtime remains deterministic offline and is checked
    against the Kristal JCS golden vectors. Both paths reject non-finite numbers.
    """
    normalized = _normalize(value)
    try:
        import rfc8785  # type: ignore

        return rfc8785.dumps(normalized)
    except ImportError:
        return _serialize_jcs(normalized).encode("utf-8")


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def prefixed_hash(prefix: str, value: Any) -> str:
    return f"{prefix}:sha256:{sha256_hex(value)}"
