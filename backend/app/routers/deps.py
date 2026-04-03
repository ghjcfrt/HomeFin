"""
FastAPI 依赖项定义。

此模块定义了 FastAPI 的依赖项，例如数据库会话的获取。
"""

from collections.abc import Generator

from sqlalchemy.orm import Session

from ..db.database import SessionLocal


# 获取数据库会话的依赖项
def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话。

    Yields:
        Generator[Session, None, None]: 数据库会话生成器。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
