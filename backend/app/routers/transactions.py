"""
收支流水接口。

此模块提供了收支流水相关的 API 接口，包括查询、创建、更新和删除交易记录。
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import schemas
from ..db import crud
from .deps import get_db

router = APIRouter(tags=["transactions"])


# 交易记录查询接口
@router.get("/transactions", response_model=list[schemas.TransactionOut])
def list_transactions(
    db: Session = Depends(get_db),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    txn_type: str | None = Query(None),
    category: str | None = Query(None),
    amount_min: float | None = Query(None),
    amount_max: float | None = Query(None),
    keyword: str | None = Query(None),
    sort_by: str = Query("txn_date"),
    sort_order: str = Query("desc"),
):
    """
    查询交易记录。

    Args:
        db (Session): 数据库会话。
        date_from (date | None): 起始日期。
        date_to (date | None): 结束日期。
        txn_type (str | None): 交易类型。
        category (str | None): 交易分类。
        amount_min (float | None): 最小金额。
        amount_max (float | None): 最大金额。
        keyword (str | None): 关键字。
        sort_by (str): 排序字段。
        sort_order (str): 排序顺序。

    Returns:
        list[schemas.TransactionOut]: 查询结果。
    """
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=400, detail="开始日期不能晚于结束日期")
    if amount_min is not None and amount_max is not None and amount_min > amount_max:
        raise HTTPException(status_code=400, detail="最小金额不能大于最大金额")

    return crud.list_transactions(
        db,
        date_from=date_from,
        date_to=date_to,
        txn_type=txn_type,
        category=category,
        amount_min=amount_min,
        amount_max=amount_max,
        keyword=keyword,
        sort_by=sort_by,
        sort_order=sort_order,
    )


# 交易记录创建接口
@router.post("/transactions", response_model=schemas.TransactionOut)
def create_transaction(
    payload: schemas.TransactionCreate, db: Session = Depends(get_db)
):
    return crud.create_transaction(db, payload)


# 交易记录更新接口
@router.put("/transactions/{txn_id}", response_model=schemas.TransactionOut)
def update_transaction(
    txn_id: int, payload: schemas.TransactionUpdate, db: Session = Depends(get_db)
):
    updated = crud.update_transaction(db, txn_id, payload)
    if updated is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    return updated


# 批量创建交易记录接口
@router.post("/transactions/batch", response_model=list[schemas.TransactionOut])
def create_transactions_batch(
    payload: schemas.BatchTransactionCreate, db: Session = Depends(get_db)
):
    return crud.create_transactions_batch(db, payload.items)


# 交易记录删除接口
@router.delete("/transactions/{txn_id}")
def remove_transaction(txn_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_transaction(db, txn_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"message": "删除成功"}
