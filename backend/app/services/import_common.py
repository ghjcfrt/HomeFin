"""
账单导入通用数据结构与辅助逻辑。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# 导入验证错误类与问题生成函数
@dataclass
class ImportValidationError(Exception):
    code: str
    message: str
    row: int | None = None
    field: str | None = None

    def to_issue(self) -> dict[str, Any]:
        """
        将验证错误转换为问题字典。

        Returns:
            dict[str, Any]: 包含错误详细信息的字典。
        """
        return {
            "severity": "error",
            "code": self.code,
            "message": self.message,
            "row": self.row,
            "field": self.field,
        }


# 问题生成函数
def make_issue(
    code: str,
    message: str,
    severity: str = "warning",
    row: int | None = None,
    field: str | None = None,
) -> dict[str, Any]:
    """
    创建问题字典。

    Args:
        code (str): 错误代码。
        message (str): 错误信息。

    Returns:
        dict[str, Any]: 包含问题详细信息的字典。
    """
    return {
        "severity": severity,
        "code": code,
        "message": message,
        "row": row,
        "field": field,
    }
