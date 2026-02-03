from __future__ import annotations

import time
from typing import Any

from app.storage.database import Database


class HashtagsRepository:
    def __init__(self, db: Database):
        self.db = db
        self._all_tags_cache: list[str] | None = None
        self._all_tags_cache_ts: float = 0.0
        self._all_tags_cache_ttl = 60.0

    def _invalidate_cache(self) -> None:
        self._all_tags_cache = None
        self._all_tags_cache_ts = 0.0

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

    async def list_all(self) -> list[str]:
        now = time.monotonic()
        if (
            self._all_tags_cache is not None
            and now - self._all_tags_cache_ts < self._all_tags_cache_ttl
        ):
            return list(self._all_tags_cache)
        rows = await self.db.fetch(
            """
            SELECT tag
            FROM hashtags
            ORDER BY tag ASC
            """,
        )
        tags = [row['tag'] for row in rows]
        self._all_tags_cache = tags
        self._all_tags_cache_ts = now
        return list(tags)

    async def create(self, tag: str) -> dict[str, Any]:
        row = await self.db.fetchrow(
            """
            INSERT INTO hashtags (tag)
            VALUES ($1)
            RETURNING id, tag, created_at
            """,
            tag,
        )
        self._invalidate_cache()
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
        if row:
            self._invalidate_cache()
            return dict(row)
        return None
