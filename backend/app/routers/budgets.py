"""
预算管理接口。

此模块提供了预算相关的 API 接口，包括获取预算状态和更新预算。
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..db import crud
from .deps import get_db

router = APIRouter(tags=["budgets"])


# 私有函数：验证月份格式
def _validate_month(month: str) -> str:
    """
    验证月份格式是否为 YYYY-MM。

    Args:
        month (str): 输入的月份字符串。

    Returns:
        str: 验证通过的月份字符串。

    Raises:
        HTTPException: 如果格式不合法，抛出 400 错误。
    """
    try:
        datetime.strptime(f"{month}-01", "%Y-%m-%d")
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="month 必须为 YYYY-MM 格式"
        ) from exc
    return month


# 预算状态查询接口
@router.get("/budgets/{month}", response_model=schemas.MonthlyBudgetStatus)
def get_budget_status(month: str, db: Session = Depends(get_db)):
    """
    获取指定月份的预算状态。

    Args:
        month (str): 月份字符串，格式为 YYYY-MM。
        db (Session): 数据库会话。

    Returns:
        schemas.MonthlyBudgetStatus: 月度预算状态。
    """
    month = _validate_month(month)
    return crud.get_monthly_budget_status(db, month)


# 预算更新接口
@router.put("/budgets/{month}", response_model=schemas.MonthlyBudgetStatus)
def upsert_month_budget(
    month: str, payload: schemas.BudgetUpsertRequest, db: Session = Depends(get_db)
):
    """
    更新或插入指定月份的预算。

    Args:
        month (str): 月份字符串，格式为 YYYY-MM。
        payload (schemas.BudgetUpsertRequest): 预算更新数据。
        db (Session): 数据库会话。

    Returns:
        schemas.MonthlyBudgetStatus: 更新后的月度预算状态。
    """
    month = _validate_month(month)
    crud.upsert_monthly_budget(
        db,
        month=month,
        total_budget=payload.total_budget,
        category_budgets=payload.category_budgets,
    )
    return crud.get_monthly_budget_status(db, month)
