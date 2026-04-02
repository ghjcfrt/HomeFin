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


class TransactionUpdate(BaseModel):
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


class ImportIssue(BaseModel):
    severity: Literal["error", "warning"]
    code: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=200)
    row: Optional[int] = Field(default=None, ge=1)
    field: Optional[str] = Field(default=None, max_length=64)


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
    issues: list[ImportIssue] = Field(default_factory=list)
    can_import: bool = True


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
    issues: list[ImportIssue] = Field(default_factory=list)
    can_import: bool = True


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
    issues: list[ImportIssue] = Field(default_factory=list)
    can_import: bool = True


class WechatImportPayload(BaseModel):
    items: list[WechatImportCandidateItem] = Field(min_length=1, max_length=2000)


class WechatImportResult(BaseModel):
    inserted: int
    skipped: int


class BudgetCategoryItem(BaseModel):
    category: str = Field(min_length=1, max_length=50)
    amount: float = Field(gt=0)


class BudgetUpsertRequest(BaseModel):
    total_budget: Optional[float] = Field(default=None, gt=0)
    category_budgets: list[BudgetCategoryItem] = Field(
        default_factory=list, max_length=200
    )


class BudgetCategoryStatusItem(BaseModel):
    category: str
    budget: float
    spent: float
    ratio: float
    level: Literal["normal", "warning", "over"]


class MonthlyBudgetStatus(BaseModel):
    month: str
    total_budget: Optional[float] = None
    total_spent: float
    total_ratio: Optional[float] = None
    total_level: Optional[Literal["normal", "warning", "over"]] = None
    category_status: list[BudgetCategoryStatusItem]


class BackupExportPayload(BaseModel):
    version: str
    exported_at: str
    transactions: list[TransactionOut]
    budgets: list[dict]


class BackupRestoreResult(BaseModel):
    restored_transactions: int
    restored_budgets: int
