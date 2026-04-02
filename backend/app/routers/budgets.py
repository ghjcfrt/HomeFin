from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..db import crud
from .deps import get_db

router = APIRouter(tags=["budgets"])


def _validate_month(month: str) -> str:
    try:
        datetime.strptime(f"{month}-01", "%Y-%m-%d")
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="month 必须为 YYYY-MM 格式"
        ) from exc
    return month


@router.get("/budgets/{month}", response_model=schemas.MonthlyBudgetStatus)
def get_budget_status(month: str, db: Session = Depends(get_db)):
    month = _validate_month(month)
    return crud.get_monthly_budget_status(db, month)


@router.put("/budgets/{month}", response_model=schemas.MonthlyBudgetStatus)
def upsert_month_budget(
    month: str, payload: schemas.BudgetUpsertRequest, db: Session = Depends(get_db)
):
    month = _validate_month(month)
    crud.upsert_monthly_budget(
        db,
        month=month,
        total_budget=payload.total_budget,
        category_budgets=payload.category_budgets,
    )
    return crud.get_monthly_budget_status(db, month)
