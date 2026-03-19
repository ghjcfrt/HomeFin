from datetime import date
from typing import Literal, Optional

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


class CategoryOptions(BaseModel):
    income: list[str]
    expense: list[str]


class OCRCandidateItem(BaseModel):
    selected: bool = True
    type: TxnType
    category: str = Field(min_length=1, max_length=50)
    amount: float = Field(gt=0)
    note: Optional[str] = Field(default=None, max_length=200)
    txn_date: date


class OCRPreviewResponse(BaseModel):
    raw_text: str
    items: list[OCRCandidateItem]
    categories: CategoryOptions


class BatchTransactionCreate(BaseModel):
    items: list[TransactionCreate] = Field(min_length=1, max_length=200)


class AlipayImportCandidateItem(BaseModel):
    selected: bool = True
    type: TxnType
    category: str = Field(min_length=1, max_length=50)
    amount: float = Field(gt=0)
    note: Optional[str] = Field(default=None, max_length=200)
    txn_date: date
    external_id: str = Field(min_length=1, max_length=64)
    source: str = Field(default="alipay_csv", min_length=1, max_length=30)
    import_key: str = Field(min_length=32, max_length=64)


class AlipayPreviewResponse(BaseModel):
    guide_url: str
    required_headers: list[str]
    items: list[AlipayImportCandidateItem]


class AlipayImportPayload(BaseModel):
    items: list[AlipayImportCandidateItem] = Field(min_length=1, max_length=2000)


class AlipayImportResult(BaseModel):
    inserted: int
    skipped: int


class WechatImportCandidateItem(BaseModel):
    selected: bool = True
    type: TxnType
    category: str = Field(min_length=1, max_length=50)
    amount: float = Field(gt=0)
    note: Optional[str] = Field(default=None, max_length=200)
    txn_date: date
    external_id: str = Field(min_length=1, max_length=64)
    source: str = Field(default="wechat_xlsx", min_length=1, max_length=30)
    import_key: str = Field(min_length=32, max_length=64)


class WechatPreviewResponse(BaseModel):
    required_headers: list[str]
    items: list[WechatImportCandidateItem]


class WechatImportPayload(BaseModel):
    items: list[WechatImportCandidateItem] = Field(min_length=1, max_length=2000)


class WechatImportResult(BaseModel):
    inserted: int
    skipped: int
