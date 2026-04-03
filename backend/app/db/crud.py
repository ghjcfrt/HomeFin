"""
数据库 CRUD 与统计查询实现。

此模块包含对数据库的增删改查操作，以及统计查询的实现。
"""

from sqlalchemy import case, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import schemas
from . import models

BUDGET_TOTAL_CATEGORY = "__TOTAL__"


# 创建单条交易记录
def create_transaction(
    db: Session, payload: schemas.TransactionCreate
) -> models.Transaction:
    """
    创建单条交易记录。

    Args:
        db (Session): 数据库会话。
        payload (schemas.TransactionCreate): 交易记录的创建数据。

    Returns:
        models.Transaction: 创建的交易记录对象。
    """
    txn = models.Transaction(**payload.model_dump())
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


# 批量创建交易记录
def create_transactions_batch(
    db: Session, items: list[schemas.TransactionCreate]
) -> list[models.Transaction]:
    """
    批量创建交易记录。

    Args:
        db (Session): 数据库会话。
        items (list[schemas.TransactionCreate]): 交易记录的创建数据列表。

    Returns:
        list[models.Transaction]: 创建的交易记录对象列表。
    """
    txns = [models.Transaction(**payload.model_dump()) for payload in items]
    db.add_all(txns)
    db.commit()
    for txn in txns:
        db.refresh(txn)
    return txns


# 查询交易记录列表
def list_transactions(
    db: Session,
    date_from=None,
    date_to=None,
    txn_type: str | None = None,
    category: str | None = None,
    amount_min: float | None = None,
    amount_max: float | None = None,
    keyword: str | None = None,
    sort_by: str = "txn_date",
    sort_order: str = "desc",
) -> list[models.Transaction]:
    """
    查询交易记录列表。

    Args:
        db (Session): 数据库会话。
        date_from (Optional[date]): 起始日期。
        date_to (Optional[date]): 结束日期。
        txn_type (Optional[str]): 交易类型。
        category (Optional[str]): 交易分类。
        amount_min (Optional[float]): 最小金额。
        amount_max (Optional[float]): 最大金额。
        keyword (Optional[str]): 搜索关键字。
        sort_by (str): 排序字段，默认为 "txn_date"。
        sort_order (str): 排序顺序，默认为 "desc"。

    Returns:
        list[models.Transaction]: 查询到的交易记录列表。
    """
    query = db.query(models.Transaction)

    if date_from is not None:
        query = query.filter(models.Transaction.txn_date >= date_from)
    if date_to is not None:
        query = query.filter(models.Transaction.txn_date <= date_to)
    if txn_type:
        query = query.filter(models.Transaction.type == txn_type)
    if category:
        query = query.filter(models.Transaction.category == category)
    if amount_min is not None:
        query = query.filter(models.Transaction.amount >= amount_min)
    if amount_max is not None:
        query = query.filter(models.Transaction.amount <= amount_max)
    if keyword:
        query = query.filter(
            or_(
                models.Transaction.note.ilike(f"%{keyword}%"),
                models.Transaction.category.ilike(f"%{keyword}%"),
            )
        )

    if sort_by and hasattr(models.Transaction, sort_by):
        sort_column = getattr(models.Transaction, sort_by)
        if sort_order == "desc":
            sort_column = sort_column.desc()
        query = query.order_by(sort_column)

    return query.all()


# 更新交易记录
def update_transaction(
    db: Session, txn_id: int, payload: schemas.TransactionUpdate
) -> models.Transaction | None:
    """
    更新交易记录。

    Args:
        db (Session): 数据库会话。
        txn_id (int): 交易记录的 ID。
        payload (schemas.TransactionUpdate): 更新数据。

    Returns:
        models.Transaction: 更新后的交易记录对象。
    """
    txn = db.query(models.Transaction).filter(models.Transaction.id == txn_id).first()
    if not txn:
        return None

    for key, value in payload.model_dump().items():
        setattr(txn, key, value)

    db.commit()
    db.refresh(txn)
    return txn


# 删除交易记录
def delete_transaction(db: Session, txn_id: int) -> bool:
    """
    删除交易记录。

    Args:
        db (Session): 数据库会话。
        txn_id (int): 交易记录的 ID。

    Returns:
        bool: 删除是否成功。
    """
    txn = db.query(models.Transaction).filter(models.Transaction.id == txn_id).first()
    if not txn:
        return False

    db.delete(txn)
    db.commit()
    return True


# 按分类汇总交易记录
def summary_by_category(db: Session, txn_type: str):
    """
    按分类汇总交易记录。

    Args:
        db (Session): 数据库会话。
        txn_type (str): 交易类型。

    Returns:
        list[dict]: 分类汇总结果。
    """
    query = (
        db.query(
            models.Transaction.category,
            func.sum(models.Transaction.amount).label("total"),
        )
        .filter(models.Transaction.type == txn_type)
        .group_by(models.Transaction.category)
    )
    return query.all()


# 按月份汇总交易记录
def summary_by_month(db: Session):
    """
    按月份汇总交易记录。

    Args:
        db (Session): 数据库会话。

    Returns:
        list[dict]: 月份汇总结果。
    """
    query = db.query(
        func.strftime("%Y-%m", models.Transaction.txn_date).label("month"),
        func.sum(
            case(
                (models.Transaction.type == "income", models.Transaction.amount),
                else_=0,
            )
        ).label("income"),
        func.sum(
            case(
                (models.Transaction.type == "expense", models.Transaction.amount),
                else_=0,
            )
        ).label("expense"),
    ).group_by("month")
    return query.all()


# 批量创建交易记录（幂等性）
def create_transactions_batch_idempotent(
    db: Session, items: list[dict]
) -> tuple[list[models.Transaction], int]:
    """
    批量创建交易记录（幂等性）。

    Args:
        db (Session): 数据库会话。
        items (list[dict]): 交易记录的创建数据列表。

    Returns:
        tuple[list[models.Transaction], int]: 创建的交易记录列表和跳过数量。
    """
    created: list[models.Transaction] = []
    skipped = 0

    for item in items:
        txn = models.Transaction(**item)
        try:
            with db.begin_nested():
                db.add(txn)
                db.flush()
            created.append(txn)
        except IntegrityError:
            skipped += 1

    db.commit()
    for txn in created:
        db.refresh(txn)

    return created, skipped


# 更新或插入月度预算
def upsert_monthly_budget(
    db: Session,
    month: str,
    total_budget: float | None,
    category_budgets: list[schemas.BudgetCategoryItem],
) -> list[models.Budget]:
    """
    更新或插入月度预算。

    Args:
        db (Session): 数据库会话。
        month (str): 月份，格式为 "YYYY-MM"。
        budgets (list[schemas.BudgetCategoryItem]): 分类预算列表。

    Returns:
        list[models.Budget]: 更新后的预算记录。
    """
    existing_rows = db.query(models.Budget).filter(models.Budget.month == month).all()
    existing_map: dict[str, models.Budget] = {
        str(getattr(row, "category")): row for row in existing_rows
    }

    total_row = existing_map.get(BUDGET_TOTAL_CATEGORY)
    if total_budget is None:
        if total_row is not None:
            db.delete(total_row)
    else:
        if total_row is not None:
            setattr(total_row, "amount", float(total_budget))
        else:
            db.add(
                models.Budget(
                    month=month,
                    category=BUDGET_TOTAL_CATEGORY,
                    amount=float(total_budget),
                )
            )

    for budget in category_budgets:
        existing_row = existing_map.get(budget.category)
        if existing_row is not None:
            setattr(existing_row, "amount", float(budget.amount))
        else:
            db.add(
                models.Budget(
                    month=month, category=budget.category, amount=float(budget.amount)
                )
            )

    db.commit()
    return db.query(models.Budget).filter(models.Budget.month == month).all()


# 根据预算使用率计算警告级别
def _to_level(ratio: float) -> str:
    """
    根据预算使用率计算警告级别。

    Args:
        ratio (float): 预算使用率，范围为 0.0 到正无穷。

    Returns:
        str: 警告级别，可选值为 "normal"、"warning" 或 "over"。
    """
    if ratio >= 1:
        return "over"
    if ratio >= 0.8:
        return "warning"
    return "normal"


# 获取月度预算状态
def get_monthly_budget_status(db: Session, month: str) -> schemas.MonthlyBudgetStatus:
    """
    获取月度预算状态。

    Args:
        db (Session): 数据库会话。
        month (str): 月份，格式为 "YYYY-MM"。

    Returns:
        schemas.MonthlyBudgetStatus: 月度预算状态。
    """
    budget_rows = db.query(models.Budget).filter(models.Budget.month == month).all()
    budget_map: dict[str, float] = {
        str(getattr(row, "category")): float(getattr(row, "amount"))
        for row in budget_rows
    }

    total_budget = budget_map.get(BUDGET_TOTAL_CATEGORY)
    category_budget_map = {
        category: amount
        for category, amount in budget_map.items()
        if category != BUDGET_TOTAL_CATEGORY
    }

    expense_rows = (
        db.query(
            models.Transaction.category.label("category"),
            func.coalesce(func.sum(models.Transaction.amount), 0).label("spent"),
        )
        .filter(models.Transaction.type == "expense")
        .filter(func.strftime("%Y-%m", models.Transaction.txn_date) == month)
        .group_by(models.Transaction.category)
        .all()
    )
    spent_map: dict[str, float] = {
        str(getattr(row, "category")): float(getattr(row, "spent") or 0)
        for row in expense_rows
    }

    category_status = []
    for category, budget_amount in category_budget_map.items():
        spent = spent_map.get(category, 0.0)
        ratio = spent / budget_amount if budget_amount > 0 else 0.0
        category_status.append(
            schemas.BudgetCategoryStatusItem(
                category=category,
                spent=spent,
                budget=budget_amount,
                ratio=ratio,
                level=_to_level(ratio),
            )
        )

    total_spent = sum(spent_map.values())
    total_ratio = (
        total_spent / total_budget if total_budget and total_budget > 0 else 0.0
    )

    return schemas.MonthlyBudgetStatus(
        month=month,
        total_budget=total_budget,
        total_spent=total_spent,
        total_ratio=total_ratio,
        total_level=_to_level(total_ratio)
        if total_budget and total_budget > 0
        else "normal",
        category_status=category_status,
    )
