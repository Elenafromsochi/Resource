from __future__ import annotations

from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import POSTGRES_URL


class Base(DeclarativeBase):
    pass


def _normalize_postgres_async_url(url: str) -> str:
    if not url:
        return url
    try:
        parsed_url = make_url(url)
    except Exception:
        return url

    if parsed_url.drivername in {"postgresql", "postgresql+psycopg2", "postgres"}:
        return parsed_url.set(drivername="postgresql+asyncpg").render_as_string(
            hide_password=False
        )

    return url


engine = create_async_engine(_normalize_postgres_async_url(POSTGRES_URL), echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
