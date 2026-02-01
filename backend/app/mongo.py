from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings

logger = logging.getLogger(__name__)
_mongo_client: AsyncIOMotorClient | None = None


def get_mongo_client() -> AsyncIOMotorClient:
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = AsyncIOMotorClient(settings.mongo_url)
    return _mongo_client


def get_mongo_db():
    return get_mongo_client()[settings.mongo_db]


async def log_channel_event(event_type: str, payload: Dict[str, Any]) -> None:
    try:
        collection = get_mongo_db().channel_events
        await collection.insert_one(
            {
                "event_type": event_type,
                "payload": payload,
                "created_at": datetime.now(timezone.utc),
            }
        )
    except Exception as exc:  # pragma: no cover - logging only
        logger.warning("Failed to log event to MongoDB: %s", exc)


async def ping_mongo() -> bool:
    try:
        await get_mongo_client().admin.command("ping")
        return True
    except Exception:
        return False
