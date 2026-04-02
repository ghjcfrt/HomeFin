from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ImportValidationError(Exception):
    code: str
    message: str
    row: int | None = None
    field: str | None = None

    def to_issue(self) -> dict[str, Any]:
        return {
            "severity": "error",
            "code": self.code,
            "message": self.message,
            "row": self.row,
            "field": self.field,
        }


def make_issue(
    code: str,
    message: str,
    severity: str = "warning",
    row: int | None = None,
    field: str | None = None,
) -> dict[str, Any]:
    return {
        "severity": severity,
        "code": code,
        "message": message,
        "row": row,
        "field": field,
    }
