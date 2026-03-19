from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import models
from .db.database import engine
from .routers import imports_router, stats_router, system_router, transactions_router

models.Base.metadata.create_all(bind=engine)


def ensure_import_columns_and_indexes() -> None:
    with engine.begin() as conn:
        table_info = conn.exec_driver_sql("PRAGMA table_info(transactions)").fetchall()
        column_names = {row[1] for row in table_info}

        if "source" not in column_names:
            conn.exec_driver_sql(
                "ALTER TABLE transactions ADD COLUMN source VARCHAR(30)"
            )

        if "import_key" not in column_names:
            conn.exec_driver_sql(
                "ALTER TABLE transactions ADD COLUMN import_key VARCHAR(64)"
            )

        conn.exec_driver_sql(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_transactions_source_import_key "
            "ON transactions (source, import_key)"
        )


ensure_import_columns_and_indexes()

app = FastAPI(title="家庭财务小管家 API", version="0.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system_router)
app.include_router(transactions_router)
app.include_router(stats_router)
app.include_router(imports_router)
