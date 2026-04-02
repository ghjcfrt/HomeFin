from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import schemas
from ..db import crud
from .deps import get_db

router = APIRouter(tags=["transactions"])


@router.get("/transactions", response_model=list[schemas.TransactionOut])
def get_transactions(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    txn_type: str | None = Query(default=None, pattern="^(income|expense)$"),
    category: str | None = Query(default=None),
    amount_min: float | None = Query(default=None, ge=0),
    amount_max: float | None = Query(default=None, ge=0),
    keyword: str | None = Query(default=None, max_length=100),
    sort_by: str = Query(
        default="txn_date", pattern="^(txn_date|amount|created_at|category|id)$"
    ),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
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


@router.post("/transactions", response_model=schemas.TransactionOut)
def create_transaction(
    payload: schemas.TransactionCreate, db: Session = Depends(get_db)
):
    return crud.create_transaction(db, payload)


@router.put("/transactions/{txn_id}", response_model=schemas.TransactionOut)
def update_transaction(
    txn_id: int, payload: schemas.TransactionUpdate, db: Session = Depends(get_db)
):
    updated = crud.update_transaction(db, txn_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="记录不存在")
    return updated


@router.post("/transactions/batch", response_model=list[schemas.TransactionOut])
def create_transactions_batch(
    payload: schemas.BatchTransactionCreate, db: Session = Depends(get_db)
):
    return crud.create_transactions_batch(db, payload.items)


@router.delete("/transactions/{txn_id}")
def remove_transaction(txn_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_transaction(db, txn_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"message": "删除成功"}
