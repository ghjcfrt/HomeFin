from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import schemas
from ..db import crud
from ..services import alipay_import_service, wechat_import_service
from ..services.ocr_service import run_ocr
from .deps import get_db

router = APIRouter(tags=["imports"])


@router.post("/ocr/preview", response_model=schemas.OCRPreviewResponse)
async def preview_ocr(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="仅支持图片文件")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="图片内容为空")

    try:
        return run_ocr(content)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"OCR 识别失败: {exc}") from exc


@router.post("/imports/alipay/preview", response_model=schemas.AlipayPreviewResponse)
async def preview_alipay_import(file: UploadFile = File(...)):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="CSV 文件内容为空")

    try:
        items = alipay_import_service.parse_alipay_csv(content)
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail=f"支付宝 CSV 解析失败: {exc}"
        ) from exc

    return {
        "guide_url": alipay_import_service.ALIPAY_GUIDE_URL,
        "required_headers": alipay_import_service.REQUIRED_HEADERS_DISPLAY,
        "items": items,
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
        raise HTTPException(status_code=400, detail="仅支持微信账单 XLSX 文件")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="XLSX 文件内容为空")

    try:
        items = wechat_import_service.parse_wechat_xlsx(content)
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail=f"微信 XLSX 解析失败: {exc}"
        ) from exc

    return {
        "required_headers": wechat_import_service.REQUIRED_HEADERS_DISPLAY,
        "items": items,
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
