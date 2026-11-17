"""数据库引擎与会话。本地无 Postgres 时回退 SQLite。"""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("DATA_DIR", ROOT / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_SQLITE = f"sqlite:///{(DATA_DIR / 'paper_agent.db').as_posix()}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_SQLITE)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, future=True, connect_args=connect_args)


if DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

if DATABASE_URL.startswith("postgresql"):

    @event.listens_for(engine, "connect")
    def _register_pgvector(dbapi_connection, _connection_record):
        try:
            from pgvector.psycopg import register_vector

            register_vector(dbapi_connection)
        except Exception:
            # 扩展未装好时不阻断普通查询
            pass


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from backend.app import models  # noqa: F401
    from backend.app.services.llm_settings import seed_llm_settings

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_llm_settings(db)
    finally:
        db.close()
