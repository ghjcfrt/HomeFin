from fastapi import APIRouter

from .. import schemas
from ..core.constants import EXPENSE_CATEGORIES, INCOME_CATEGORIES

router = APIRouter(tags=["system"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/categories", response_model=schemas.CategoryOptions)
def get_categories() -> dict[str, list[str]]:
    return {
        "income": INCOME_CATEGORIES,
        "expense": EXPENSE_CATEGORIES,
    }
