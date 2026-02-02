from __future__ import annotations

from typing import Any
from typing import Optional
import logging

from telethon import TelegramClient
from telethon import functions
from telethon import types
from telethon.errors import RPCError
from telethon.sessions import StringSession

from app.config import TELEGRAM_API_HASH
from app.config import TELEGRAM_API_ID
from app.config import TELETHON_SESSION


logger = logging.getLogger(__name__)


async def resolve_channel(username: str) -> Optional[dict[str, Any]]:
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
        entity_id = getattr(entity, 'id', None)
        return {
            'id': entity_id,
            'title': title or entity_username,
            'username': entity_username,
        }
    except (RPCError, Exception) as exc:
        logger.warning('Telethon failed for %s: %s', username, exc)
        return None
    finally:
        await client.disconnect()


async def search_channels(query: str, limit: int = 10) -> list[dict[str, Any]]:
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        return []

    client = TelegramClient(
        StringSession(TELETHON_SESSION),
        TELEGRAM_API_ID,
        TELEGRAM_API_HASH,
    )

    try:
        await client.connect()
        result = await client(
            functions.contacts.SearchRequest(
                q=query,
                limit=limit,
            ),
        )
        channels: list[dict[str, Any]] = []
        for chat in result.chats:
            if not isinstance(chat, types.Channel) or chat.megagroup:
                continue

            description = None
            try:
                full = await client(functions.channels.GetFullChannelRequest(chat))
                description = getattr(full.full_chat, 'about', None)
            except (RPCError, Exception) as exc:
                logger.warning(
                    'Telethon failed to fetch channel details for %s: %s',
                    chat.id,
                    exc,
                )

            channels.append(
                {
                    'id': chat.id,
                    'title': chat.title or chat.username or str(chat.id),
                    'username': chat.username,
                    'description': description,
                },
            )
        return channels
    except (RPCError, Exception) as exc:
        logger.warning('Telethon channel search failed for %s: %s', query, exc)
        return []
    finally:
        await client.disconnect()
