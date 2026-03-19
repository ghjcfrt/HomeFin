from datetime import date
from typing import Optional, Literal

from pydantic import BaseModel, Field


TxnType = Literal["income", "expense"]


class TransactionCreate(BaseModel):
    type: TxnType
    category: str = Field(min_length=1, max_length=50)
    amount: float = Field(gt=0)
    note: Optional[str] = Field(default=None, max_length=200)
    txn_date: date


class TransactionOut(TransactionCreate):
    id: int

    class Config:
        from_attributes = True


class CategorySummaryItem(BaseModel):
    category: str
    total: float


class MonthlySummaryItem(BaseModel):
    month: str
    income: float
    expense: float
    balance: float
