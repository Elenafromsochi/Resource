from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from telethon import TelegramClient
from telethon.errors import RPCError

from app.config import settings

logger = logging.getLogger(__name__)


async def resolve_channel(username: str) -> Optional[Dict[str, Any]]:
    if not settings.telegram_api_id or not settings.telegram_api_hash:
        return None

    client = TelegramClient(
        settings.telethon_session,
        settings.telegram_api_id,
        settings.telegram_api_hash,
    )

    try:
        await client.connect()
        if settings.telegram_bot_token:
            await client.start(bot_token=settings.telegram_bot_token)

        entity = await client.get_entity(username)
        if entity is None:
            return None

        title = getattr(entity, "title", None)
        entity_username = getattr(entity, "username", None) or username
        return {"name": title or entity_username, "username": entity_username}
    except (RPCError, Exception) as exc:
        logger.warning("Telethon failed for %s: %s", username, exc)
        return None
    finally:
        await client.disconnect()
