"""
系统基础信息接口。

此模块提供了系统相关的基础信息接口，例如健康检查和分类选项。
"""

from fastapi import APIRouter

from .. import schemas
from ..core.constants import EXPENSE_CATEGORIES, INCOME_CATEGORIES

router = APIRouter(tags=["system"])


# 健康检查接口
@router.get("/health")
def health_check() -> dict[str, str]:
    """
    健康检查接口。

    Returns:
        dict[str, str]: 系统健康状态。
    """
    return {"status": "ok"}


# 分类选项接口
@router.get("/categories", response_model=schemas.CategoryOptions)
def get_categories() -> dict[str, list[str]]:
    """
    获取收入和支出分类选项。

    Returns:
        dict[str, list[str]]: 包含收入和支出的分类选项。
    """
    return {
        "income": INCOME_CATEGORIES,
        "expense": EXPENSE_CATEGORIES,
    }
