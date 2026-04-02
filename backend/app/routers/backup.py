import json
from datetime import date, datetime
from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import schemas
from ..db import models
from .deps import get_db

router = APIRouter(tags=["backup"])


def _normalize_date(value: str) -> date:
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="备份文件中的日期格式不合法"
        ) from exc


@router.get("/backup/export")
def export_backup(db: Session = Depends(get_db)):
    txns = db.query(models.Transaction).order_by(models.Transaction.id.asc()).all()
    budgets = (
        db.query(models.Budget)
        .order_by(models.Budget.month.asc(), models.Budget.category.asc())
        .all()
    )

    payload = {
        "version": "1.0",
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "transactions": [
            {
                "type": row.type,
                "category": row.category,
                "amount": row.amount,
                "note": row.note,
                "txn_date": str(row.txn_date),
                "source": row.source,
                "import_key": row.import_key,
            }
            for row in txns
        ],
        "budgets": [
            {
                "month": row.month,
                "category": row.category,
                "amount": row.amount,
            }
            for row in budgets
        ],
    }

    content = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    filename = f"homefin-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(
        BytesIO(content), media_type="application/json", headers=headers
    )


@router.post("/backup/restore", response_model=schemas.BackupRestoreResult)
async def restore_backup(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="备份文件内容为空")

    try:
        payload = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=400, detail="备份文件不是合法的 UTF-8 JSON"
        ) from exc

    transactions = payload.get("transactions")
    budgets = payload.get("budgets", [])
    if not isinstance(transactions, list) or not isinstance(budgets, list):
        raise HTTPException(
            status_code=400,
            detail="备份文件结构不匹配，缺少 transactions 或 budgets 列表",
        )

    restored_txn_count = 0
    restored_budget_count = 0

    try:
        with db.begin():
            db.query(models.Transaction).delete()
            db.query(models.Budget).delete()

            for item in transactions:
                db.add(
                    models.Transaction(
                        type=str(item.get("type") or "").strip(),
                        category=str(item.get("category") or "").strip(),
                        amount=float(item.get("amount")),
                        note=(
                            str(item.get("note"))
                            if item.get("note") is not None
                            else None
                        ),
                        txn_date=_normalize_date(item.get("txn_date")),
                        source=(
                            str(item.get("source"))
                            if item.get("source") is not None
                            else None
                        ),
                        import_key=(
                            str(item.get("import_key"))
                            if item.get("import_key") is not None
                            else None
                        ),
                    )
                )
                restored_txn_count += 1

            for item in budgets:
                month = str(item.get("month") or "").strip()
                category = str(item.get("category") or "").strip()
                if not month or not category:
                    raise HTTPException(
                        status_code=400, detail="预算备份项缺少 month 或 category"
                    )
                db.add(
                    models.Budget(
                        month=month,
                        category=category,
                        amount=float(item.get("amount")),
                    )
                )
                restored_budget_count += 1

    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400, detail=f"备份文件字段值不合法: {exc}"
        ) from exc
    except IntegrityError as exc:
        raise HTTPException(
            status_code=400, detail="备份数据存在重复键冲突，恢复已取消"
        ) from exc

    return {
        "restored_transactions": restored_txn_count,
        "restored_budgets": restored_budget_count,
    }
