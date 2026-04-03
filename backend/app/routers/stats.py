"""
统计分析接口。

此模块提供了统计相关的 API 接口，包括按分类和按月的统计汇总。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..db import crud
from .deps import get_db

router = APIRouter(tags=["stats"])  # 统计分析相关的路由，统一使用 "stats" 标签


# 分类统计汇总接口
@router.get(
    "/stats/category/{txn_type}", response_model=list[schemas.CategorySummaryItem]
)
def get_category_summary(txn_type: str, db: Session = Depends(get_db)):
    """
    获取按分类的统计汇总。

    Args:
        txn_type (str): 交易类型，可选值为 "income" 或 "expense"。
        db (Session): 数据库会话。

    Returns:
        list[schemas.CategorySummaryItem]: 分类统计汇总。

    Raises:
        HTTPException: 如果 txn_type 不合法，抛出 400 错误。
    """
    if txn_type not in {"income", "expense"}:
        raise HTTPException(status_code=400, detail="txn_type 必须是 income 或 expense")
    return crud.summary_by_category(db, txn_type)


# 按月统计汇总接口
@router.get("/stats/monthly", response_model=list[schemas.MonthlySummaryItem])
def get_monthly_summary(db: Session = Depends(get_db)):
    """
    获取按月的统计汇总。

    Args:
        db (Session): 数据库会话。

    Returns:
        list[schemas.MonthlySummaryItem]: 月度统计汇总。
    """
    return crud.summary_by_month(db)
