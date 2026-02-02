from __future__ import annotations

from typing import Any

from app.storage.database import Database


class ChannelsRepository:
    def __init__(self, db: Database):
        self.db = db

    async def get_by_id(self, channel_id: int) -> dict[str, Any] | None:
        row = await self.db.fetchrow(
            """
            SELECT id, username, title, created_at
            FROM channels
            WHERE id = $1
            """,
            channel_id,
        )
        return dict(row) if row else None

    async def get_by_username(self, username: str) -> dict[str, Any] | None:
        row = await self.db.fetchrow(
            """
            SELECT id, username, title, created_at
            FROM channels
            WHERE username = $1
            """,
            username,
        )
        return dict(row) if row else None

    async def list(self) -> list[dict[str, Any]]:
        rows = await self.db.fetch(
            """
            SELECT id, username, title, created_at
            FROM channels
            ORDER BY created_at DESC
            """,
        )
        return [dict(row) for row in rows]

    async def list_by_ids(self, channel_ids: list[int]) -> list[dict[str, Any]]:
        rows = await self.db.fetch(
            """
            SELECT id, username, title, created_at
            FROM channels
            WHERE id = ANY($1::BIGINT[])
            ORDER BY created_at DESC
            """,
            channel_ids,
        )
        return [dict(row) for row in rows]

    async def list_by_usernames(self, usernames: list[str]) -> list[dict[str, Any]]:
        if not usernames:
            return []
        rows = await self.db.fetch(
            """
            SELECT id, username, title, created_at
            FROM channels
            WHERE username = ANY($1::VARCHAR[])
            ORDER BY created_at DESC
            """,
            usernames,
        )
        return [dict(row) for row in rows]

    async def create(
        self,
        channel_id: int,
        username: str | None,
        title: str | None,
    ) -> dict[str, Any]:
        row = await self.db.fetchrow(
            """
            INSERT INTO channels (id, username, title)
            VALUES ($1, $2, $3)
            RETURNING id, username, title, created_at
            """,
            channel_id,
            username,
            title,
        )
        return dict(row)

    async def delete(self, channel_id: int) -> dict[str, Any] | None:
        row = await self.db.fetchrow(
            """
            DELETE FROM channels
            WHERE id = $1
            RETURNING id, username, title, created_at
            """,
            channel_id,
        )
        return dict(row) if row else None
