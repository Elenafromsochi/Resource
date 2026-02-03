from __future__ import annotations

from typing import Any

import asyncpg


class Database:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    @classmethod
    async def connect(cls, dsn: str) -> "Database":
        pool = await asyncpg.create_pool(dsn)
        return cls(pool)

    async def close(self) -> None:
        await self.pool.close()

    async def fetchrow(self, query: str, *args: Any) -> asyncpg.Record | None:
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetch(self, query: str, *args: Any) -> list[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchval(self, query: str, *args: Any) -> Any:
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def execute(self, query: str, *args: Any) -> str:
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def executemany(self, query: str, args: list[tuple[Any, ...]]) -> None:
        if not args:
            return
        async with self.pool.acquire() as conn:
            await conn.executemany(query, args)

    async def execute_script(self, sql: str) -> None:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(sql)
