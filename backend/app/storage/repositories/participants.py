from __future__ import annotations

from datetime import datetime
from typing import Any
import base64

from app.storage.database import Database


def build_photo_url(photo_bytes: bytes | None, photo_mime: str | None) -> str | None:
    if not photo_bytes or not photo_mime:
        return None
    encoded = base64.b64encode(photo_bytes).decode("ascii")
    return f"data:{photo_mime};base64,{encoded}"


class ParticipantsRepository:
    def __init__(self, db: Database):
        self.db = db

    def _row_to_dict(self, row: Any) -> dict[str, Any]:
        payload = dict(row)
        photo_bytes = payload.pop("photo_bytes", None)
        photo_mime = payload.pop("photo_mime", None)
        payload["photo_url"] = build_photo_url(photo_bytes, photo_mime)
        return payload

    async def list(self, limit: int, offset: int) -> tuple[list[dict[str, Any]], int]:
        rows = await self.db.fetch(
            """
            SELECT user_id,
                   username,
                   first_name,
                   last_name,
                   display_name,
                   about,
                   is_bot,
                   is_verified,
                   is_scam,
                   is_fake,
                   is_restricted,
                   photo_bytes,
                   photo_mime,
                   last_seen_at,
                   profile_updated_at,
                   created_at,
                   updated_at
            FROM participants
            ORDER BY last_seen_at DESC NULLS LAST,
                     profile_updated_at DESC NULLS LAST
            LIMIT $1 OFFSET $2
            """,
            limit,
            offset,
        )
        total = await self.db.fetchval("SELECT COUNT(*) FROM participants")
        return [self._row_to_dict(row) for row in rows], int(total or 0)

    async def get_by_id(self, user_id: int) -> dict[str, Any] | None:
        row = await self.db.fetchrow(
            """
            SELECT user_id,
                   username,
                   first_name,
                   last_name,
                   display_name,
                   about,
                   is_bot,
                   is_verified,
                   is_scam,
                   is_fake,
                   is_restricted,
                   photo_bytes,
                   photo_mime,
                   last_seen_at,
                   profile_updated_at,
                   created_at,
                   updated_at
            FROM participants
            WHERE user_id = $1
            """,
            user_id,
        )
        return self._row_to_dict(row) if row else None

    async def ensure_minimal(
        self,
        last_seen_map: dict[int, datetime],
        now: datetime,
    ) -> None:
        if not last_seen_map:
            return
        query = """
            INSERT INTO participants (
                user_id,
                display_name,
                last_seen_at,
                created_at,
                updated_at
            )
            VALUES ($1, $2, $3, $4, $4)
            ON CONFLICT (user_id) DO NOTHING
        """
        args: list[tuple[Any, ...]] = []
        for user_id, last_seen in last_seen_map.items():
            args.append(
                (
                    user_id,
                    None,
                    last_seen,
                    now,
                ),
            )
        await self.db.executemany(query, args)

    async def upsert_details(self, participants: list[dict[str, Any]]) -> None:
        if not participants:
            return
        query = """
            INSERT INTO participants (
                user_id,
                username,
                first_name,
                last_name,
                display_name,
                about,
                is_bot,
                is_verified,
                is_scam,
                is_fake,
                is_restricted,
                photo_id,
                photo_bytes,
                photo_mime,
                profile_updated_at,
                updated_at,
                created_at
            )
            VALUES (
                $1, $2, $3, $4, $5, $6,
                $7, $8, $9, $10, $11,
                $12, $13, $14, $15, $16, $16
            )
            ON CONFLICT (user_id) DO UPDATE SET
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                display_name = EXCLUDED.display_name,
                about = EXCLUDED.about,
                is_bot = EXCLUDED.is_bot,
                is_verified = EXCLUDED.is_verified,
                is_scam = EXCLUDED.is_scam,
                is_fake = EXCLUDED.is_fake,
                is_restricted = EXCLUDED.is_restricted,
                photo_id = EXCLUDED.photo_id,
                photo_bytes = EXCLUDED.photo_bytes,
                photo_mime = EXCLUDED.photo_mime,
                profile_updated_at = EXCLUDED.profile_updated_at,
                updated_at = EXCLUDED.updated_at
        """
        args: list[tuple[Any, ...]] = []
        for item in participants:
            args.append(
                (
                    item["user_id"],
                    item.get("username"),
                    item.get("first_name"),
                    item.get("last_name"),
                    item.get("display_name"),
                    item.get("about"),
                    item.get("is_bot", False),
                    item.get("is_verified", False),
                    item.get("is_scam", False),
                    item.get("is_fake", False),
                    item.get("is_restricted", False),
                    item.get("photo_id"),
                    item.get("photo_bytes"),
                    item.get("photo_mime"),
                    item.get("profile_updated_at"),
                    item.get("updated_at"),
                ),
            )
        await self.db.executemany(query, args)

    async def update_last_seen(self, last_seen_map: dict[int, datetime]) -> None:
        if not last_seen_map:
            return
        query = """
            UPDATE participants
            SET last_seen_at = CASE
                    WHEN last_seen_at IS NULL THEN $2
                    WHEN $2 IS NULL THEN last_seen_at
                    WHEN $2 > last_seen_at THEN $2
                    ELSE last_seen_at
                END,
                updated_at = $3
            WHERE user_id = $1
        """
        now = datetime.now(timezone.utc)
        args = [(user_id, last_seen, now) for user_id, last_seen in last_seen_map.items()]
        await self.db.executemany(query, args)
