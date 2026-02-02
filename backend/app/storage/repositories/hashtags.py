from __future__ import annotations

from typing import Any

from app.storage.database import Database


class HashtagsRepository:
    def __init__(self, db: Database):
        self.db = db

    async def get_by_tag(self, tag: str) -> dict[str, Any] | None:
        row = await self.db.fetchrow(
            """
            SELECT id, tag, created_at
            FROM hashtags
            WHERE tag = $1
            """,
            tag,
        )
        return dict(row) if row else None

    async def list(self, limit: int, offset: int) -> tuple[list[dict[str, Any]], int]:
        rows = await self.db.fetch(
            """
            SELECT id, tag, created_at
            FROM hashtags
            ORDER BY created_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit,
            offset,
        )
        total = await self.db.fetchval("SELECT COUNT(*) FROM hashtags")
        return [dict(row) for row in rows], int(total or 0)

    async def create(self, tag: str) -> dict[str, Any]:
        row = await self.db.fetchrow(
            """
            INSERT INTO hashtags (tag)
            VALUES ($1)
            RETURNING id, tag, created_at
            """,
            tag,
        )
        return dict(row)

    async def delete(self, hashtag_id: int) -> dict[str, Any] | None:
        row = await self.db.fetchrow(
            """
            DELETE FROM hashtags
            WHERE id = $1
            RETURNING id, tag, created_at
            """,
            hashtag_id,
        )
        return dict(row) if row else None
