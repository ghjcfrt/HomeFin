from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..db import crud
from .deps import get_db

router = APIRouter(tags=["stats"])


@router.get(
    "/stats/category/{txn_type}", response_model=list[schemas.CategorySummaryItem]
)
def get_category_summary(txn_type: str, db: Session = Depends(get_db)):
    if txn_type not in {"income", "expense"}:
        raise HTTPException(status_code=400, detail="txn_type 必须是 income 或 expense")
    return crud.summary_by_category(db, txn_type)


@router.get("/stats/monthly", response_model=list[schemas.MonthlySummaryItem])
def get_monthly_summary(db: Session = Depends(get_db)):
    return crud.summary_by_month(db)
