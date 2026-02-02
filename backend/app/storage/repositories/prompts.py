from __future__ import annotations

from typing import Any

from app.storage.database import Database


class PromptsRepository:
    def __init__(self, db: Database):
        self.db = db

    async def list(self) -> list[dict[str, Any]]:
        rows = await self.db.fetch(
            """
            SELECT id, name, content, created_at, updated_at
            FROM analysis_prompts
            ORDER BY created_at DESC
            """,
        )
        return [dict(row) for row in rows]

    async def get_by_id(self, prompt_id: int) -> dict[str, Any] | None:
        row = await self.db.fetchrow(
            """
            SELECT id, name, content, created_at, updated_at
            FROM analysis_prompts
            WHERE id = $1
            """,
            prompt_id,
        )
        return dict(row) if row else None

    async def create(self, name: str, content: str) -> dict[str, Any]:
        row = await self.db.fetchrow(
            """
            INSERT INTO analysis_prompts (name, content)
            VALUES ($1, $2)
            RETURNING id, name, content, created_at, updated_at
            """,
            name,
            content,
        )
        return dict(row)

    async def update(
        self,
        prompt_id: int,
        *,
        name: str | None = None,
        content: str | None = None,
    ) -> dict[str, Any] | None:
        row = await self.db.fetchrow(
            """
            UPDATE analysis_prompts
            SET name = COALESCE($2, name),
                content = COALESCE($3, content),
                updated_at = NOW()
            WHERE id = $1
            RETURNING id, name, content, created_at, updated_at
            """,
            prompt_id,
            name,
            content,
        )
        return dict(row) if row else None

    async def delete(self, prompt_id: int) -> dict[str, Any] | None:
        row = await self.db.fetchrow(
            """
            DELETE FROM analysis_prompts
            WHERE id = $1
            RETURNING id, name, content, created_at, updated_at
            """,
            prompt_id,
        )
        return dict(row) if row else None
