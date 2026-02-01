from __future__ import annotations

from typing import Any
from typing import Dict
from typing import Optional
import logging

from telethon import TelegramClient
from telethon import utils
from telethon.errors import RPCError
from telethon.sessions import StringSession
from telethon.tl.types import Channel as TgChannel
from telethon.tl.types import Chat as TgChat

from app.config import TELEGRAM_API_HASH
from app.config import TELEGRAM_API_ID
from app.config import TELETHON_SESSION


logger = logging.getLogger(__name__)


def telethon_configured() -> bool:
    return bool(TELEGRAM_API_ID and TELEGRAM_API_HASH and TELETHON_SESSION)


def _dialog_type(entity: Any) -> Optional[str]:
    if isinstance(entity, TgChannel):
        if getattr(entity, 'broadcast', False):
            return 'channel'
        if getattr(entity, 'megagroup', False):
            return 'group'
        return 'channel'
    if isinstance(entity, TgChat):
        return 'group'
    return None


def _dialog_name(entity: Any) -> str:
    title = getattr(entity, 'title', None)
    username = getattr(entity, 'username', None)
    return title or username or str(getattr(entity, 'id', 'unknown'))


def _build_dialog_payload(entity: Any) -> Optional[Dict[str, Any]]:
    dialog_type = _dialog_type(entity)
    if dialog_type is None:
        return None
    return {
        'tg_peer_id': utils.get_peer_id(entity),
        'username': getattr(entity, 'username', None),
        'name': _dialog_name(entity),
        'dialog_type': dialog_type,
    }


async def resolve_channel(username: str) -> Optional[Dict[str, Any]]:
    if not telethon_configured():
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

        payload = _build_dialog_payload(entity)
        if payload is None:
            return None
        entity_username = payload.get('username') or username
        payload['username'] = entity_username
        payload['name'] = payload.get('name') or entity_username
        return payload
    except (RPCError, Exception) as exc:
        logger.warning('Telethon failed for %s: %s', username, exc)
        return None
    finally:
        await client.disconnect()


async def fetch_dialog_channels() -> list[Dict[str, Any]]:
    if not telethon_configured():
        return []

    client = TelegramClient(
        StringSession(TELETHON_SESSION),
        TELEGRAM_API_ID,
        TELEGRAM_API_HASH,
    )

    try:
        await client.connect()
        if not await client.is_user_authorized():
            logger.warning('Telethon session is not authorized')
            return []

        dialogs: list[Dict[str, Any]] = []
        async for dialog in client.iter_dialogs():
            payload = _build_dialog_payload(dialog.entity)
            if payload:
                dialogs.append(payload)
        return dialogs
    except (RPCError, Exception) as exc:
        logger.warning('Telethon dialog sync failed: %s', exc)
        return []
    finally:
        await client.disconnect()
