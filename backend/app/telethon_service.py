from __future__ import annotations

from typing import Any
from typing import Dict
from typing import Optional
import logging
import os
from pathlib import Path

from telethon import TelegramClient
from telethon.errors import RPCError

from app.config import TELEGRAM_API_HASH
from app.config import TELEGRAM_API_ID
from app.config import TELETHON_SESSION


logger = logging.getLogger(__name__)


def _prepare_session_path(session_value: str) -> str:
    session_value = (session_value or '').strip()
    if not session_value:
        session_value = 'telethon'

    path = Path(session_value).expanduser()
    if session_value.endswith(os.sep) or (path.exists() and path.is_dir()):
        path = path / 'telethon'

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.warning(
            'Unable to create Telethon session directory %s: %s',
            path.parent,
            exc,
        )

    return str(path)


async def resolve_channel(username: str) -> Optional[Dict[str, Any]]:
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        return None

    client: Optional[TelegramClient] = None
    try:
        session_path = _prepare_session_path(TELETHON_SESSION)
        client = TelegramClient(
            session_path,
            TELEGRAM_API_ID,
            TELEGRAM_API_HASH,
        )

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
        if client is not None:
            await client.disconnect()
