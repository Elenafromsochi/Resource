from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import POSTGRES_URL


class Base(DeclarativeBase):
    pass


engine = create_async_engine(POSTGRES_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text(
                'ALTER TABLE channels '
                'ADD COLUMN IF NOT EXISTS tg_peer_id BIGINT',
            ),
        )
        await conn.execute(
            text(
                "ALTER TABLE channels "
                "ADD COLUMN IF NOT EXISTS dialog_type VARCHAR(20) "
                "NOT NULL DEFAULT 'channel'",
            ),
        )
        await conn.execute(
            text(
                "UPDATE channels SET dialog_type = 'channel' "
                "WHERE dialog_type IS NULL",
            ),
        )
        await conn.execute(
            text('ALTER TABLE channels ALTER COLUMN username DROP NOT NULL'),
        )
        await conn.execute(
            text(
                'CREATE UNIQUE INDEX IF NOT EXISTS '
                'channels_tg_peer_id_key ON channels (tg_peer_id)',
            ),
        )
        await conn.execute(
            text(
                'CREATE INDEX IF NOT EXISTS '
                'ix_channels_username ON channels (username)',
            ),
        )
