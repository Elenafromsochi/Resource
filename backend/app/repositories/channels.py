from __future__ import annotations

from typing import Any

from app.database import Database


class ChannelsRepository:
    def __init__(self, db: Database):
        self._db = db

    async def get_by_username(self, username: str) -> dict[str, Any] | None:
        row = await self._db.fetchrow(
            """
            SELECT id, username, name, created_at
            FROM channels
            WHERE username = $1
            """,
            username,
        )
        return dict(row) if row else None

    async def list(self) -> list[dict[str, Any]]:
        rows = await self._db.fetch(
            """
            SELECT id, username, name, created_at
            FROM channels
            ORDER BY created_at DESC
            """,
        )
        return [dict(row) for row in rows]

    async def create(self, username: str, name: str) -> dict[str, Any]:
        row = await self._db.fetchrow(
            """
            INSERT INTO channels (username, name)
            VALUES ($1, $2)
            RETURNING id, username, name, created_at
            """,
            username,
            name,
        )
        return dict(row)

    async def delete(self, channel_id: int) -> dict[str, Any] | None:
        row = await self._db.fetchrow(
            """
            DELETE FROM channels
            WHERE id = $1
            RETURNING id, username, name, created_at
            """,
            channel_id,
        )
        return dict(row) if row else None
