"""SQLAlchemy ORM 数据表模型定义。"""

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    UniqueConstraint,
    func,
)

from .database import Base


# 交易表模型
class Transaction(Base):
    __tablename__ = "transactions"  # 交易记录表

    id = Column(
        Integer, primary_key=True, index=True
    )  # 交易记录的唯一标识符，自动递增。
    type = Column(String(20), nullable=False)  # income / expense
    category = Column(String(50), nullable=False)  # 交易分类
    amount = Column(Float, nullable=False)  # 交易金额，正数表示收入，负数表示支出
    note = Column(String(200), nullable=True)  # 备注信息，最长 200 字符
    txn_date = Column(Date, nullable=False)  # 交易日期
    source = Column(String(30), nullable=True, index=True)  # 交易来源，如 "alipay_csv"
    import_key = Column(
        String(64), nullable=True, index=True
    )  # 导入去重键，最长 64 字符
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )  # 记录创建时间，默认为当前时间


# 预算表模型
class Budget(Base):
    __tablename__ = "budgets"  # 预算表，记录每月的预算金额，按月和分类进行唯一约束
    __table_args__ = (
        UniqueConstraint("month", "category", name="ux_budgets_month_category"),
    )  # month 和 category 的组合必须唯一，确保同一月同一分类只有一个预算记录

    id = Column(
        Integer, primary_key=True, index=True
    )  # 预算记录的唯一标识符，自动递增。
    month = Column(
        String(7), nullable=False, index=True
    )  # YYYY-MM 格式的月份字符串，表示预算所属的月份
    category = Column(String(50), nullable=False, index=True)  # 预算分类
    amount = Column(Float, nullable=False)  # 预算金额，必须为非负数
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )  # 记录创建时间，默认为当前时间
