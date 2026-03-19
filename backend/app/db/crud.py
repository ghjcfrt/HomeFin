from sqlalchemy import case, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import schemas
from . import models


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


def list_transactions(db: Session) -> list[models.Transaction]:
    return (
        db.query(models.Transaction)
        .order_by(models.Transaction.txn_date.desc(), models.Transaction.id.desc())
        .all()
    )


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
