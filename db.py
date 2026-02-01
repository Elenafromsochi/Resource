from __future__ import annotations

from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from models.base import Base

_ENGINE = None
_SESSION_FACTORY: async_sessionmaker[AsyncSession] | None = None


def init_engine(database_url: str) -> None:
    global _ENGINE, _SESSION_FACTORY
    if _ENGINE is not None:
        return
    _ENGINE = create_async_engine(database_url, echo=False, future=True)
    _SESSION_FACTORY = async_sessionmaker(
        _ENGINE,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


async def init_db(database_url: str) -> None:
    init_engine(database_url)
    async with _ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_session() -> async_sessionmaker[AsyncSession]:
    if _SESSION_FACTORY is None:
        raise RuntimeError("DB session factory not initialized")
    return _SESSION_FACTORY


async def session_scope() -> AsyncIterator[AsyncSession]:
    session_factory = get_session()
    async with session_factory() as session:
        yield session
