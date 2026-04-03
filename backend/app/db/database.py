"""
数据库连接、会话工厂与基类定义。

此模块负责配置数据库连接、会话工厂和 ORM 基类，
以支持应用程序的数据库操作。
"""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# 项目根目录的路径。
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# SQLite 数据库文件的路径。
DB_PATH = PROJECT_ROOT / "homefin.db"

# 数据库连接 URL，使用 SQLite。
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

"""
SQLAlchemy 数据库引擎。
配置参数：
- check_same_thread: False，允许多线程访问。
"""
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

"""
SQLAlchemy 会话工厂
配置参数：
- autocommit: False，禁用自动提交。
- autoflush: False，禁用自动刷新。
- bind: 绑定到数据库引擎。
"""
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# SQLAlchemy ORM 模型的基类。
Base = declarative_base()
