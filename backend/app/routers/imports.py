"""
账单导入接口。

此模块提供了账单导入相关的 API 接口，包括 OCR 预览、支付宝账单导入和微信账单导入。
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import schemas
from ..db import crud
from ..services import alipay_import_service, wechat_import_service
from ..services.import_common import ImportValidationError
from ..services.ocr_service import run_ocr
from .deps import get_db

router = APIRouter(tags=["imports"])  # 账单导入相关接口的路由器


# 抛出导入错误的统一方法
def _raise_import_error(
    code: str,
    message: str,
    status_code: int = 400,
    severity: str = "error",
    row: int | None = None,
    field: str | None = None,
):
    """
    抛出导入错误。

    Args:
        code (str): 错误代码。
        message (str): 错误信息。
        status_code (int): HTTP 状态码，默认为 400。
        severity (str): 错误严重性，默认为 "error"。
        row (int | None): 错误所在行，默认为 None。
        field (str | None): 错误字段，默认为 None。

    Raises:
        HTTPException: 包含错误详细信息的 HTTP 异常。
    """
    # 抛出 HTTP 异常，包含错误代码、信息、严重性、所在行和字段等详细信息
    raise HTTPException(
        status_code=status_code,
        detail={
            "code": code,
            "message": message,
            "severity": severity,
            "row": row,
            "field": field,
        },
    )


# OCR 预览接口
@router.post("/ocr/preview", response_model=schemas.OCRPreviewResponse)
async def preview_ocr(file: UploadFile = File(...)):
    """
    路由：OCR 预览

    处理 POST 请求，接收上传的图片文件并返回 OCR 识别结果。

    参数：
        - file: 上传的图片文件，必须是合法的图片格式。

    返回：
        - 包含 OCR 识别结果的字典。
    """
    # 验证文件类型和内容
    if not file.content_type or not file.content_type.startswith("image/"):
        _raise_import_error(
            code="OCR_INVALID_FILE_TYPE",
            message="仅支持图片文件",
            field="file",
        )
    # 读取上传的文件内容
    content = await file.read()
    # 如果文件内容为空，返回 400 错误
    if not content:
        _raise_import_error(
            code="IMPORT_EMPTY_FILE",
            message="图片内容为空",
            field="file",
        )
    # 调用 OCR 服务，返回识别结果
    try:
        result = run_ocr(content)
        result["issues"] = []
        result["can_import"] = bool(result.get("items"))
        return result
    # 如果 OCR 识别过程中出现验证错误，返回包含错误详细信息的 400 错误
    except ImportValidationError as exc:
        _raise_import_error(
            code=exc.code,
            message=exc.message,
            field=exc.field,
            row=exc.row,
        )
    # 如果 OCR 识别过程中出现其他错误，返回包含错误信息的 500 错误
    except Exception as exc:
        _raise_import_error(
            code="OCR_PREVIEW_FAILED",
            message=f"OCR 识别失败: {exc}",
            status_code=500,
        )


# 支付宝账单预览接口
@router.post("/imports/alipay/preview", response_model=schemas.AlipayPreviewResponse)
async def preview_alipay_import(file: UploadFile = File(...)):
    """
    路由：支付宝账单预览

    处理 POST 请求，接收上传的支付宝账单 CSV 文件并返回解析结果。

    参数：
        - file: 上传的 CSV 文件。

    返回：
        - 包含解析结果的字典。
    """
    # 验证文件类型和内容
    content = await file.read()
    # 如果文件内容为空，返回 400 错误
    if not content:
        _raise_import_error(
            code="IMPORT_EMPTY_FILE",
            message="CSV 文件内容为空",
            field="file",
        )
    # 调用支付宝账单解析服务，返回解析结果
    try:
        items, issues = alipay_import_service.parse_alipay_csv(content)
    # 如果解析过程中出现验证错误，返回包含错误详细信息的 400 错误
    except ImportValidationError as exc:
        _raise_import_error(
            code=exc.code,
            message=exc.message,
            field=exc.field,
            row=exc.row,
        )
    # 如果解析过程中出现其他错误，返回包含错误信息的 500 错误
    except Exception as exc:
        _raise_import_error(
            code="ALIPAY_PREVIEW_FAILED",
            message=f"支付宝 CSV 解析失败: {exc}",
        )

    return {
        "guide_url": alipay_import_service.ALIPAY_GUIDE_URL,
        "required_headers": alipay_import_service.REQUIRED_HEADERS_DISPLAY,
        "items": items,
        "issues": issues,
        "can_import": bool(items),
    }


# 支付宝账单导入接口
@router.post("/imports/alipay", response_model=schemas.AlipayImportResult)
def import_alipay(payload: schemas.AlipayImportPayload, db: Session = Depends(get_db)):
    """
    路由：支付宝账单导入

    处理 POST 请求，接收支付宝账单数据并导入数据库。

    参数：
        - payload: 支付宝账单导入数据。
        - db: 数据库会话对象。

    返回：
        - 包含导入结果的字典。
    """
    # 将导入数据转换为数据库模型需要的格式
    normalized_items = []
    # 遍历导入数据中的每一项，提取必要的字段并构建一个新的字典，添加到 normalized_items 列表中
    for item in payload.items:
        normalized_items.append(
            {
                "type": item.type,
                "category": item.category,
                "amount": item.amount,
                "txn_date": item.txn_date,
                "note": item.note,
                "source": item.source,
                "import_key": item.import_key,
            }
        )
    # 批量创建交易记录，返回创建的记录列表和跳过的数量
    created, skipped = crud.create_transactions_batch_idempotent(db, normalized_items)
    return {"inserted": len(created), "skipped": skipped}


# 微信账单预览接口
@router.post("/imports/wechat/preview", response_model=schemas.WechatPreviewResponse)
async def preview_wechat_import(file: UploadFile = File(...)):
    """
    路由：微信账单预览

    处理 POST 请求，接收上传的微信账单 XLSX 文件并返回解析结果。

    参数：
        - file: 上传的 XLSX 文件。

    返回：
        - 包含解析结果的字典。
    """
    # 验证文件类型和内容
    if file.filename and not file.filename.lower().endswith(".xlsx"):
        _raise_import_error(
            code="WECHAT_INVALID_FILE_TYPE",
            message="仅支持微信账单 XLSX 文件",
            field="file",
        )

    # 读取上传的文件内容
    content = await file.read()

    # 如果文件内容为空，返回 400 错误
    if not content:
        _raise_import_error(
            code="IMPORT_EMPTY_FILE",
            message="XLSX 文件内容为空",
            field="file",
        )

    # 调用微信账单解析服务，返回解析结果
    try:
        items, issues = wechat_import_service.parse_wechat_xlsx(content)
    except ImportValidationError as exc:
        # 如果解析过程中出现验证错误，返回包含错误详细信息的 400 错误
        _raise_import_error(
            code=exc.code,
            message=exc.message,
            field=exc.field,
            row=exc.row,
        )
    except Exception as exc:
        # 如果解析过程中出现其他错误，返回包含错误信息的 500 错误
        _raise_import_error(
            code="WECHAT_PREVIEW_FAILED",
            message=f"微信 XLSX 解析失败: {exc}",
        )

    return {
        "required_headers": wechat_import_service.REQUIRED_HEADERS_DISPLAY,
        "items": items,
        "issues": issues,
        "can_import": bool(items),
    }


# 微信账单导入接口
@router.post("/imports/wechat", response_model=schemas.WechatImportResult)
def import_wechat(payload: schemas.WechatImportPayload, db: Session = Depends(get_db)):
    """
    路由：微信账单导入

    处理 POST 请求，接收微信账单数据并导入数据库。

    参数：
        - payload: 微信账单导入数据。
        - db: 数据库会话对象。

    返回：
        - 包含导入结果的字典。
    """
    # 将导入数据转换为数据库模型需要的格式
    normalized_items = []
    # 遍历导入数据中的每一项，提取必要的字段并构建一个新的字典，添加到 normalized_items 列表中
    for item in payload.items:
        normalized_items.append(
            {
                "type": item.type,
                "category": item.category,
                "amount": item.amount,
                "txn_date": item.txn_date,
                "note": item.note,
                "source": item.source,
                "import_key": item.import_key,
            }
        )
    # 批量创建交易记录，返回创建的记录列表和跳过的数量
    created, skipped = crud.create_transactions_batch_idempotent(db, normalized_items)
    return {"inserted": len(created), "skipped": skipped}
