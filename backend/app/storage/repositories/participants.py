from __future__ import annotations

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
                   photo_bytes,
                   photo_mime
            FROM participants
            ORDER BY user_id DESC
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
                   photo_bytes,
                   photo_mime
            FROM participants
            WHERE user_id = $1
            """,
            user_id,
        )
        if not row:
            return None
        payload = self._row_to_dict(row)
        payload["channels"] = await self.list_channels_for_user(user_id)
        return payload

    async def list_by_ids(self, user_ids: list[int]) -> list[dict[str, Any]]:
        if not user_ids:
            return []
        rows = await self.db.fetch(
            """
            SELECT user_id,
                   username,
                   first_name,
                   last_name,
                   display_name,
                   about,
                   photo_bytes
            FROM participants
            WHERE user_id = ANY($1::BIGINT[])
            """,
            user_ids,
        )
        return [dict(row) for row in rows]

    async def list_channels_for_user(self, user_id: int) -> list[dict[str, Any]]:
        rows = await self.db.fetch(
            """
            SELECT channels.id,
                   channels.username,
                   channels.title
            FROM participant_channels
            JOIN channels ON channels.id = participant_channels.channel_id
            WHERE participant_channels.participant_id = $1
            ORDER BY channels.title NULLS LAST, channels.id
            """,
            user_id,
        )
        return [dict(row) for row in rows]

    async def ensure_minimal(self, user_ids: set[int]) -> None:
        if not user_ids:
            return
        query = """
            INSERT INTO participants (
                user_id
            )
            VALUES ($1)
            ON CONFLICT (user_id) DO NOTHING
        """
        args: list[tuple[Any, ...]] = [(user_id,) for user_id in user_ids]
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
                photo_bytes,
                photo_mime
            )
            VALUES (
                $1, $2, $3, $4, $5, $6,
                $7, $8
            )
            ON CONFLICT (user_id) DO UPDATE SET
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                display_name = EXCLUDED.display_name,
                about = EXCLUDED.about,
                photo_bytes = EXCLUDED.photo_bytes,
                photo_mime = EXCLUDED.photo_mime
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
                    item.get("photo_bytes"),
                    item.get("photo_mime"),
                ),
            )
        await self.db.executemany(query, args)

    async def upsert_channel_links(self, pairs: set[tuple[int, int]]) -> None:
        if not pairs:
            return
        query = """
            INSERT INTO participant_channels (
                participant_id,
                channel_id
            )
            VALUES ($1, $2)
            ON CONFLICT (participant_id, channel_id) DO NOTHING
        """
        args = [(participant_id, channel_id) for participant_id, channel_id in pairs]
        await self.db.executemany(query, args)

