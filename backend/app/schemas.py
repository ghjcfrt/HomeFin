"""
Pydantic 数据模型定义。

此模块定义了用于数据验证和序列化的 Pydantic 模型，
包括交易记录、分类汇总、月度汇总等相关数据结构。
"""

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field

TxnType = Literal["income", "expense"]


# 交易记录模型
class TransactionCreate(BaseModel):
    """
    创建交易记录的模型。

    Attributes:
        type (TxnType): 交易类型，可选值为 "income" 或 "expense"。
        category (str): 交易分类，长度限制为 1 到 50 个字符。
        amount (float): 交易金额，必须大于 0。
        note (Optional[str]): 备注信息，最长 200 个字符。
        txn_date (date): 交易日期。
    """

    type: TxnType
    category: str = Field(min_length=1, max_length=50)
    amount: float = Field(gt=0)
    note: Optional[str] = Field(default=None, max_length=200)
    txn_date: date


# 更新交易记录的模型，允许修改所有字段
class TransactionUpdate(BaseModel):
    """
    更新交易记录的模型。

    Attributes:
        type (TxnType): 交易类型，可选值为 "income" 或 "expense"。
        category (str): 交易分类，长度限制为 1 到 50 个字符。
    """

    type: TxnType
    category: str = Field(min_length=1, max_length=50)
    amount: float = Field(gt=0)
    note: Optional[str] = Field(default=None, max_length=200)
    txn_date: date


# 输出交易记录的模型，包含数据库中的 id 字段
class TransactionOut(TransactionCreate):
    """
    输出交易记录的模型，继承自 TransactionCreate。

    Attributes:
        id (int): 交易记录的唯一标识符。
    """

    id: int

    class Config:
        from_attributes = True


# 预算记录模型
class CategorySummaryItem(BaseModel):
    """
    分类汇总项的模型。

    Attributes:
        category (str): 分类名称。
        total (float): 分类的总金额。
    """

    category: str
    total: float


# 月度汇总模型
class MonthlySummaryItem(BaseModel):
    """
    月度汇总项的模型。

    Attributes:
        month (str): 月份，格式为 "YYYY-MM"。
        income (float): 月收入总额。
        expense (float): 月支出总额。
        balance (float): 月结余金额。
    """

    month: str
    income: float
    expense: float
    balance: float


# 分类选项模型
class CategoryOptions(BaseModel):
    """
    分类选项的模型。

    Attributes:
        categories (list[str]): 可用分类的列表。
    """

    income: list[str]
    expense: list[str]


# 统一导入/预览条目模型
class ImportPreviewItem(BaseModel):
    """
    导入预览条目的模型。

    Attributes:
        selected (bool): 是否默认选中。
        type (TxnType): 交易类型。
        category (str): 交易分类。
        amount (float): 金额。
        txn_date (date): 交易日期。
        note (Optional[str]): 备注。
        external_id (Optional[str]): 外部单号。
        source (Optional[str]): 导入来源。
        import_key (Optional[str]): 导入幂等键。
    """

    selected: bool = True
    type: TxnType
    category: str = Field(min_length=1, max_length=50)
    amount: float = Field(gt=0)
    txn_date: date
    note: Optional[str] = Field(default=None, max_length=200)
    external_id: Optional[str] = Field(default=None, max_length=80)
    source: Optional[str] = Field(default=None, max_length=30)
    import_key: Optional[str] = Field(default=None, max_length=64)


# 备份导出模型
class ImportIssue(BaseModel):
    """
    导入问题的模型。

    Attributes:
        issue_type (str): 问题类型。
        description (str): 问题描述。
    """

    severity: str
    code: str
    message: str
    row: int | None = None
    field: str | None = None


# OCR 识别候选项模型
class OCRCandidateItem(ImportPreviewItem):
    """OCR 候选项的模型。"""


# OCR 预览响应模型
class OCRPreviewResponse(BaseModel):
    """
    OCR 预览响应的模型。

    Attributes:
        candidates (list[OCRCandidateItem]): OCR 候选项列表。
    """

    raw_text: str = ""
    items: list[OCRCandidateItem]
    categories: CategoryOptions
    issues: list[ImportIssue] = Field(default_factory=list)
    can_import: bool = False


# OCR 导入结果模型
class BatchTransactionCreate(BaseModel):
    """
    批量交易创建的模型。

    Attributes:
        items (list[TransactionCreate]): 交易记录列表。
    """

    items: list[TransactionCreate]


# 批量创建交易记录的模型，包含多个 TransactionCreate 项
class AlipayImportCandidateItem(ImportPreviewItem):
    """支付宝导入候选项的模型。"""


# 支付宝预览响应模型
class AlipayPreviewResponse(BaseModel):
    """
    支付宝预览响应的模型。

    Attributes:
        candidates (list[AlipayImportCandidateItem]): 支付宝导入候选项列表。
    """

    guide_url: str
    required_headers: list[str]
    items: list[AlipayImportCandidateItem]
    issues: list[ImportIssue] = Field(default_factory=list)
    can_import: bool = False


class ImportTransactionCreate(TransactionCreate):
    """
    导入交易记录的模型。

    Attributes:
        source (Optional[str]): 导入来源。
        import_key (Optional[str]): 导入幂等键。
    """

    source: Optional[str] = Field(default=None, max_length=30)
    import_key: Optional[str] = Field(default=None, max_length=64)


# 支付宝导入有效负载模型
class AlipayImportPayload(BaseModel):
    """
    支付宝导入有效负载的模型。

    Attributes:
        items (list[ImportTransactionCreate]): 交易记录列表。
    """

    items: list[ImportTransactionCreate]


# 支付宝导入结果模型
class AlipayImportResult(BaseModel):
    """
    支付宝导入结果的模型。

    Attributes:
        success (bool): 导入是否成功。
        message (str): 导入结果消息。
    """

    inserted: int
    skipped: int


# 微信导入候选项模型
class WechatImportCandidateItem(ImportPreviewItem):
    """微信导入候选项的模型。"""


# 微信预览响应模型
class WechatPreviewResponse(BaseModel):
    """
    微信预览响应的模型。

    Attributes:
        candidates (list[WechatImportCandidateItem]): 微信导入候选项列表。
    """

    required_headers: list[str]
    items: list[WechatImportCandidateItem]
    issues: list[ImportIssue] = Field(default_factory=list)
    can_import: bool = False


# 微信导入有效负载模型
class WechatImportPayload(BaseModel):
    """
    微信导入有效负载的模型。

    Attributes:
        items (list[ImportTransactionCreate]): 交易记录列表。
    """

    items: list[ImportTransactionCreate]


# 微信导入结果模型
class WechatImportResult(BaseModel):
    """
    微信导入结果的模型。

    Attributes:
        success (bool): 导入是否成功。
        message (str): 导入结果消息。
    """

    restored_transactions: int
    restored_budgets: int


# 预算分类项模型
class BudgetCategoryItem(BaseModel):
    """
    预算分类项的模型。

    Attributes:
        category (str): 分类名称。
        amount (float): 分类预算金额。
    """

    category: str = Field(min_length=1, max_length=50)
    amount: float = Field(gt=0)


# 预算更新请求模型
class BudgetUpsertRequest(BaseModel):
    """
    预算更新请求的模型。

    Attributes:
        month (str): 月份，格式为 "YYYY-MM"。
        categories (list[BudgetCategoryItem]): 分类预算列表。
    """

    total_budget: float | None = Field(default=None, gt=0)
    category_budgets: list[BudgetCategoryItem] = Field(default_factory=list)


# 预算分类状态项模型
class BudgetCategoryStatusItem(BaseModel):
    """
    预算分类状态项的模型。

    Attributes:
        category (str): 分类名称。
        spent (float): 已花费金额。
        budget (float): 预算金额。
    """

    category: str
    spent: float
    budget: float
    ratio: float
    level: str


# 月度预算状态模型
class MonthlyBudgetStatus(BaseModel):
    """
    月度预算状态的模型。

    Attributes:
        month (str): 月份，格式为 "YYYY-MM"。
        categories (list[BudgetCategoryStatusItem]): 分类状态列表。
    """

    month: str
    total_budget: float | None = None
    total_spent: float
    total_ratio: float
    total_level: str
    category_status: list[BudgetCategoryStatusItem] = Field(default_factory=list)


# 备份导出有效负载模型
class BackupExportPayload(BaseModel):
    """
    备份导出有效负载的模型。

    Attributes:
        data (str): 导出的数据内容。
    """

    data: str


# 备份恢复结果模型
class BackupRestoreResult(BaseModel):
    """
    备份恢复结果的模型。

    Attributes:
        success (bool): 恢复是否成功。
        message (str): 恢复结果消息。
    """

    restored_transactions: int
    restored_budgets: int
