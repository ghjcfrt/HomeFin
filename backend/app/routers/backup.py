"""
备份与恢复接口。
"""

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

# 备份文件的 JSON 结构版本
router = APIRouter(tags=["backup"])


# 私有函数：规范化日期字符串
# 将输入的日期字符串转换为标准日期对象
# 如果格式不合法，抛出 HTTP 400 异常
def _normalize_date(value: str) -> date:
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="备份文件中的日期格式不合法"
        ) from exc


# 私有函数：#
@router.get("/backup/export")
def export_backup(db: Session = Depends(get_db)):
    """
    导出备份
    处理 GET 请求，查询数据库中的交易记录和预算记录，并生成一个包含这些数据的 JSON 文件供下载
    """
    # 查询所有交易记录，按 ID 升序排序
    txns = db.query(models.Transaction).order_by(models.Transaction.id.asc()).all()
    # 查询所有预算记录，按月和分类升序排序
    budgets = (
        db.query(models.Budget)
        .order_by(models.Budget.month.asc(), models.Budget.category.asc())
        .all()
    )

    # 构造导出数据的 JSON 结构
    payload = {
        "version": "1.0",  # 当前备份格式版本
        "exported_at": datetime.now().isoformat(timespec="seconds"),  # 导出时间
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

    content = json.dumps(payload, ensure_ascii=False, indent=2).encode(
        "utf-8"
    )  # 生成格式化的 JSON 字符串，便于阅读和调试
    filename = f"homefin-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"  # 生成带有时间戳的文件名，方便区分不同版本的备份
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"'
    }  # 设置响应头，提示浏览器下载文件而不是直接显示
    return StreamingResponse(
        BytesIO(content), media_type="application/json", headers=headers
    )


# 恢复备份
@router.post("/backup/restore", response_model=schemas.BackupRestoreResult)
async def restore_backup(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    路由：恢复备份
    处理 POST 请求，接收上传的备份文件并恢复到数据库
    参数：
        - file: 上传的备份文件，必须是合法的 JSON 文件
        - db: 数据库会话对象，用于执行数据库操作
    返回：
        - 包含恢复的交易记录数和预算记录数的字典
    """
    # 读取上传的文件内容
    content = await file.read()
    if not content:
        # 如果文件内容为空，返回 400 错误
        raise HTTPException(status_code=400, detail="备份文件内容为空")

    try:
        # 尝试将文件内容解析为 JSON
        payload = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        # 如果解析失败，返回 400 错误
        raise HTTPException(
            status_code=400, detail="备份文件不是合法的 UTF-8 JSON"
        ) from exc

    # 从 JSON 中提取 transactions 和 budgets 列表
    transactions = payload.get("transactions")
    budgets = payload.get("budgets", [])
    if not isinstance(transactions, list) or not isinstance(budgets, list):
        # 如果结构不匹配，返回 400 错误
        raise HTTPException(
            status_code=400,
            detail="备份文件结构不匹配，缺少 transactions 或 budgets 列表",
        )

    # 初始化恢复的记录计数器
    restored_txn_count = 0
    restored_budget_count = 0

    try:
        # 开启数据库事务
        with db.begin():
            # 清空现有的交易记录和预算记录
            db.query(models.Transaction).delete()
            db.query(models.Budget).delete()

            # 恢复交易记录
            for item in transactions:
                db.add(
                    models.Transaction(
                        type=str(item.get("type") or "").strip(),  # 交易类型
                        category=str(item.get("category") or "").strip(),  # 交易分类
                        amount=float(item.get("amount")),  # 交易金额
                        note=(
                            str(item.get("note"))
                            if item.get("note") is not None
                            else None
                        ),  # 备注
                        txn_date=_normalize_date(item.get("txn_date")),  # 交易日期
                        source=(
                            str(item.get("source"))
                            if item.get("source") is not None
                            else None
                        ),  # 来源
                        import_key=(
                            str(item.get("import_key"))
                            if item.get("import_key") is not None
                            else None
                        ),  # 导入键
                    )
                )
                restored_txn_count += 1

            # 恢复预算记录
            for item in budgets:
                month = str(item.get("month") or "").strip()  # 预算月份
                category = str(item.get("category") or "").strip()  # 预算分类
                if not month or not category:
                    # 如果缺少必要字段，返回 400 错误
                    raise HTTPException(
                        status_code=400, detail="预算备份项缺少 month 或 category"
                    )
                db.add(
                    models.Budget(
                        month=month,
                        category=category,
                        amount=float(item.get("amount")),  # 预算金额
                    )
                )
                restored_budget_count += 1

    except (TypeError, ValueError) as exc:
        # 如果字段值不合法，返回 400 错误
        raise HTTPException(
            status_code=400, detail=f"备份文件字段值不合法: {exc}"
        ) from exc
    except IntegrityError as exc:
        # 如果存在重复键冲突，返回 400 错误
        raise HTTPException(
            status_code=400, detail="备份数据存在重复键冲突，恢复已取消"
        ) from exc

    # 返回恢复的记录数
    return {
        "restored_transactions": restored_txn_count,
        "restored_budgets": restored_budget_count,
    }
