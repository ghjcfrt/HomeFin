from .backup import router as backup_router
from .budgets import router as budgets_router
from .imports import router as imports_router
from .stats import router as stats_router
from .system import router as system_router
from .transactions import router as transactions_router

__all__ = [
    "backup_router",
    "budgets_router",
    "imports_router",
    "stats_router",
    "system_router",
    "transactions_router",
]
