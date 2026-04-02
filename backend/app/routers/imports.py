from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import schemas
from ..db import crud
from ..services import alipay_import_service, wechat_import_service
from ..services.import_common import ImportValidationError
from ..services.ocr_service import run_ocr
from .deps import get_db

router = APIRouter(tags=["imports"])


def _raise_import_error(
    code: str,
    message: str,
    status_code: int = 400,
    severity: str = "error",
    row: int | None = None,
    field: str | None = None,
):
    raise HTTPException(
        status_code=status_code,
        detail={
            "severity": severity,
            "code": code,
            "message": message,
            "row": row,
            "field": field,
        },
    )


@router.post("/ocr/preview", response_model=schemas.OCRPreviewResponse)
async def preview_ocr(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        _raise_import_error(
            code="OCR_INVALID_FILE_TYPE",
            message="仅支持图片文件",
            field="file",
        )

    content = await file.read()
    if not content:
        _raise_import_error(
            code="IMPORT_EMPTY_FILE",
            message="图片内容为空",
            field="file",
        )

    try:
        result = run_ocr(content)
        result["issues"] = []
        result["can_import"] = bool(result.get("items"))
        return result
    except ImportValidationError as exc:
        _raise_import_error(
            code=exc.code,
            message=exc.message,
            field=exc.field,
            row=exc.row,
        )
    except Exception as exc:
        _raise_import_error(
            code="OCR_PREVIEW_FAILED",
            message=f"OCR 识别失败: {exc}",
            status_code=500,
        )


@router.post("/imports/alipay/preview", response_model=schemas.AlipayPreviewResponse)
async def preview_alipay_import(file: UploadFile = File(...)):
    content = await file.read()
    if not content:
        _raise_import_error(
            code="IMPORT_EMPTY_FILE",
            message="CSV 文件内容为空",
            field="file",
        )

    try:
        items, issues = alipay_import_service.parse_alipay_csv(content)
    except ImportValidationError as exc:
        _raise_import_error(
            code=exc.code,
            message=exc.message,
            field=exc.field,
            row=exc.row,
        )
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


@router.post("/imports/alipay", response_model=schemas.AlipayImportResult)
def import_alipay(payload: schemas.AlipayImportPayload, db: Session = Depends(get_db)):
    normalized_items = []
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

    created, skipped = crud.create_transactions_batch_idempotent(db, normalized_items)
    return {"inserted": len(created), "skipped": skipped}


@router.post("/imports/wechat/preview", response_model=schemas.WechatPreviewResponse)
async def preview_wechat_import(file: UploadFile = File(...)):
    if file.filename and not file.filename.lower().endswith(".xlsx"):
        _raise_import_error(
            code="WECHAT_INVALID_FILE_TYPE",
            message="仅支持微信账单 XLSX 文件",
            field="file",
        )

    content = await file.read()
    if not content:
        _raise_import_error(
            code="IMPORT_EMPTY_FILE",
            message="XLSX 文件内容为空",
            field="file",
        )

    try:
        items, issues = wechat_import_service.parse_wechat_xlsx(content)
    except ImportValidationError as exc:
        _raise_import_error(
            code=exc.code,
            message=exc.message,
            field=exc.field,
            row=exc.row,
        )
    except Exception as exc:
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


@router.post("/imports/wechat", response_model=schemas.WechatImportResult)
def import_wechat(payload: schemas.WechatImportPayload, db: Session = Depends(get_db)):
    normalized_items = []
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

    created, skipped = crud.create_transactions_batch_idempotent(db, normalized_items)
    return {"inserted": len(created), "skipped": skipped}
