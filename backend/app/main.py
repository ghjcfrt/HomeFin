"""
FastAPI 应用入口与路由注册。

此模块负责初始化 FastAPI 应用实例，配置中间件，
并注册所有路由模块。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import models
from .db.database import engine
from .routers import (
    backup_router,
    budgets_router,
    imports_router,
    stats_router,
    system_router,
    transactions_router,
)

# 创建数据库表结构
models.Base.metadata.create_all(bind=engine)


# 确保 transactions 表包含 source 和 import_key 列，并创建唯一索引
def ensure_import_columns_and_indexes() -> None:
    """
    确保数据库中的 transactions 表包含必要的列和索引。

    此函数会检查并添加以下列：
    - source: 数据来源，字符串类型，最大长度 30。
    - import_key: 导入键，字符串类型，最大长度 64。

    同时创建唯一索引：
    - ux_transactions_source_import_key: 基于 source 和 import_key 的唯一约束。
    """
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


# 确保数据库表结构和索引正确，避免重复导入数据
ensure_import_columns_and_indexes()
# 创建 FastAPI 应用实例
app = FastAPI(title="家庭财务小管家 API", version="0.0.2")

"""
添加跨域资源共享 (CORS) 中间件。

配置参数：
- allow_origins: 允许的来源，设置为 "*" 表示允许所有来源。
- allow_credentials: 是否允许发送凭据。
- allow_methods: 允许的 HTTP 方法，设置为 "*" 表示允许所有方法。
- allow_headers: 允许的 HTTP 头，设置为 "*" 表示允许所有头。
"""
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

"""
注册路由模块。

包括：
- system_router: 系统相关接口。
- transactions_router: 交易记录接口。
- stats_router: 统计分析接口。
- imports_router: 数据导入接口。
- budgets_router: 预算管理接口。
- backup_router: 数据备份与恢复接口。
"""
app.include_router(system_router)
app.include_router(transactions_router)
app.include_router(stats_router)
app.include_router(imports_router)
app.include_router(budgets_router)
app.include_router(backup_router)
