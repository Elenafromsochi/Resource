from __future__ import annotations

from typing import Any
from typing import Dict
from typing import Optional
import logging

from telethon import TelegramClient
from telethon.errors import RPCError
from telethon.sessions import StringSession

from app.config import TELEGRAM_API_HASH
from app.config import TELEGRAM_API_ID
from app.config import TELETHON_SESSION


logger = logging.getLogger(__name__)


async def resolve_channel(username: str) -> Optional[Dict[str, Any]]:
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        return None

    client = TelegramClient(
        StringSession(TELETHON_SESSION),
        TELEGRAM_API_ID,
        TELEGRAM_API_HASH,
    )

    try:
        await client.connect()
        entity = await client.get_entity(username)
        if entity is None:
            return None

        title = getattr(entity, 'title', None)
        entity_username = getattr(entity, 'username', None) or username
        return {'name': title or entity_username, 'username': entity_username}
    except (RPCError, Exception) as exc:
        logger.warning('Telethon failed for %s: %s', username, exc)
        return None
    finally:
        await client.disconnect()
