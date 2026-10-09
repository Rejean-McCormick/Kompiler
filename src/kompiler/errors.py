from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class KompilerException(Exception):
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    operation_id: str | None = None
    retryable: bool = False

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


class AdmissionError(KompilerException):
    pass


class AdapterError(KompilerException):
    pass


class CompilationError(KompilerException):
    pass


class PolicyError(KompilerException):
    pass


class StandardError(KompilerException):
    pass
