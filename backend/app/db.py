"""Подключение к БД (SQLAlchemy 2.0)."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

# pool_pre_ping — переподключение к базе, если соединение «протухло».
engine = create_engine(
    settings.database_url, connect_args=connect_args, pool_pre_ping=True, future=True
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Создать таблицы. Для прототипа — без Alembic-миграций."""
    from . import models  # noqa: F401  (регистрация моделей)

    Base.metadata.create_all(bind=engine)
    _ensure_columns()


def _ensure_columns() -> None:
    """Аккуратно добавить недостающие столбцы на уже существующей таблице.

    create_all не меняет существующие таблицы. Если БД была создана раньше без
    новых полей — добавляем их здесь. Каждый ALTER в своей транзакции; если столбец
    уже есть, ошибка игнорируется.
    """
    statements = [
        "ALTER TABLE profiles ADD COLUMN answers JSON",
    ]
    for statement in statements:
        try:
            with engine.begin() as conn:
                conn.execute(text(statement))
        except Exception:
            pass  # столбец уже существует — это нормально
