from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..db import crud
from .deps import get_db

router = APIRouter(tags=["transactions"])


@router.get("/transactions", response_model=list[schemas.TransactionOut])
def get_transactions(db: Session = Depends(get_db)):
    return crud.list_transactions(db)


@router.post("/transactions", response_model=schemas.TransactionOut)
def create_transaction(
    payload: schemas.TransactionCreate, db: Session = Depends(get_db)
):
    return crud.create_transaction(db, payload)


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
