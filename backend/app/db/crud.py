from sqlalchemy import case, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import schemas
from . import models

BUDGET_TOTAL_CATEGORY = "__TOTAL__"


def create_transaction(
    db: Session, payload: schemas.TransactionCreate
) -> models.Transaction:
    txn = models.Transaction(**payload.model_dump())
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


def create_transactions_batch(
    db: Session, items: list[schemas.TransactionCreate]
) -> list[models.Transaction]:
    txns = [models.Transaction(**payload.model_dump()) for payload in items]
    db.add_all(txns)
    db.commit()
    for txn in txns:
        db.refresh(txn)
    return txns


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
        pattern = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                models.Transaction.category.ilike(pattern),
                models.Transaction.note.ilike(pattern),
            )
        )

    sort_map = {
        "txn_date": models.Transaction.txn_date,
        "amount": models.Transaction.amount,
        "created_at": models.Transaction.created_at,
        "category": models.Transaction.category,
        "id": models.Transaction.id,
    }
    sort_col = sort_map.get(sort_by, models.Transaction.txn_date)
    if sort_order == "asc":
        query = query.order_by(sort_col.asc(), models.Transaction.id.asc())
    else:
        query = query.order_by(sort_col.desc(), models.Transaction.id.desc())

    return query.all()


def update_transaction(
    db: Session, txn_id: int, payload: schemas.TransactionUpdate
) -> models.Transaction | None:
    txn = db.query(models.Transaction).filter(models.Transaction.id == txn_id).first()
    if not txn:
        return None

    for key, value in payload.model_dump().items():
        setattr(txn, key, value)

    db.commit()
    db.refresh(txn)
    return txn


def delete_transaction(db: Session, txn_id: int) -> bool:
    txn = db.query(models.Transaction).filter(models.Transaction.id == txn_id).first()
    if not txn:
        return False
    db.delete(txn)
    db.commit()
    return True


def summary_by_category(db: Session, txn_type: str):
    return (
        db.query(
            models.Transaction.category.label("category"),
            func.sum(models.Transaction.amount).label("total"),
        )
        .filter(models.Transaction.type == txn_type)
        .group_by(models.Transaction.category)
        .order_by(func.sum(models.Transaction.amount).desc())
        .all()
    )


def summary_by_month(db: Session):
    month_expr = func.strftime("%Y-%m", models.Transaction.txn_date)

    income_sum = func.sum(
        case(
            (models.Transaction.type == "income", models.Transaction.amount), else_=0.0
        )
    )
    expense_sum = func.sum(
        case(
            (models.Transaction.type == "expense", models.Transaction.amount), else_=0.0
        )
    )

    rows = (
        db.query(
            month_expr.label("month"),
            income_sum.label("income"),
            expense_sum.label("expense"),
        )
        .group_by(month_expr)
        .order_by(month_expr)
        .all()
    )

    result = []
    for row in rows:
        income = float(row.income or 0)
        expense = float(row.expense or 0)
        result.append(
            {
                "month": row.month,
                "income": income,
                "expense": expense,
                "balance": income - expense,
            }
        )
    return result


def create_transactions_batch_idempotent(
    db: Session, items: list[dict]
) -> tuple[list[models.Transaction], int]:
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


def upsert_monthly_budget(
    db: Session,
    month: str,
    total_budget: float | None,
    category_budgets: list[schemas.BudgetCategoryItem],
) -> None:
    existing = db.query(models.Budget).filter(models.Budget.month == month).all()
    existing_map = {item.category: item for item in existing}

    incoming_map = {item.category: item.amount for item in category_budgets}

    if total_budget is not None:
        incoming_map[BUDGET_TOTAL_CATEGORY] = total_budget
    elif BUDGET_TOTAL_CATEGORY in existing_map:
        db.delete(existing_map[BUDGET_TOTAL_CATEGORY])

    for category, amount in incoming_map.items():
        row = existing_map.get(category)
        if row:
            row.amount = amount
        else:
            db.add(models.Budget(month=month, category=category, amount=amount))

    for category, row in existing_map.items():
        if category == BUDGET_TOTAL_CATEGORY:
            continue
        if category not in incoming_map:
            db.delete(row)

    db.commit()


def _to_level(ratio: float) -> str:
    if ratio >= 1:
        return "over"
    if ratio >= 0.8:
        return "warning"
    return "normal"


def get_monthly_budget_status(db: Session, month: str) -> schemas.MonthlyBudgetStatus:
    budget_rows = db.query(models.Budget).filter(models.Budget.month == month).all()
    budget_map = {row.category: float(row.amount) for row in budget_rows}

    total_spent = (
        db.query(func.sum(models.Transaction.amount))
        .filter(models.Transaction.type == "expense")
        .filter(func.strftime("%Y-%m", models.Transaction.txn_date) == month)
        .scalar()
    )
    total_spent_value = float(total_spent or 0)

    category_spent_rows = (
        db.query(models.Transaction.category, func.sum(models.Transaction.amount))
        .filter(models.Transaction.type == "expense")
        .filter(func.strftime("%Y-%m", models.Transaction.txn_date) == month)
        .group_by(models.Transaction.category)
        .all()
    )
    category_spent_map = {
        category: float(total or 0) for category, total in category_spent_rows
    }

    category_status: list[schemas.BudgetCategoryStatusItem] = []
    for category, budget in budget_map.items():
        if category == BUDGET_TOTAL_CATEGORY:
            continue
        spent = category_spent_map.get(category, 0.0)
        ratio = spent / budget if budget > 0 else 0.0
        category_status.append(
            schemas.BudgetCategoryStatusItem(
                category=category,
                budget=budget,
                spent=spent,
                ratio=round(ratio, 4),
                level=_to_level(ratio),
            )
        )

    category_status.sort(
        key=lambda x: (x.level != "over", x.level != "warning", -x.ratio, x.category)
    )

    total_budget = budget_map.get(BUDGET_TOTAL_CATEGORY)
    total_ratio = None
    total_level = None
    if total_budget is not None and total_budget > 0:
        total_ratio = round(total_spent_value / total_budget, 4)
        total_level = _to_level(total_ratio)

    return schemas.MonthlyBudgetStatus(
        month=month,
        total_budget=total_budget,
        total_spent=total_spent_value,
        total_ratio=total_ratio,
        total_level=total_level,
        category_status=category_status,
    )
