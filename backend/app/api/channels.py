from __future__ import annotations

import logging
import re
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import status

from app.api.dependencies import get_storage
from app.api.dependencies import get_telegram
from app.exceptions import ConflictError
from app.exceptions import NotFoundError
from app.exceptions import ValidationError
from app.schemas import ChannelCreate
from app.schemas import ChannelList
from app.schemas import ChannelImportSummary
from app.schemas import ChannelRead
from app.schemas import ChannelSearchList
from app.storage import Storage
from app.storage.mongo import log_channel_event
from app.telethon_service import TelegramService

router = APIRouter(prefix='/channels', tags=['channels'])
logger = logging.getLogger(__name__)


def normalize_username(raw: str) -> str:
    value = raw.strip()
    value = re.sub(r'^(https?://)?t\.me/', '', value, flags=re.IGNORECASE)
    value = re.sub(r'^(https?://)?telegram\.me/', '', value, flags=re.IGNORECASE)
    value = value.lstrip('@')
    return value.strip()


async def get_channel_by_username(
    storage: Storage,
    username: str,
) -> Optional[dict]:
    return await storage.channels.get_by_username(username)


@router.get('', response_model=ChannelList)
async def list_channels(
    storage: Storage = Depends(get_storage),
):
    items = await storage.channels.list()
    return ChannelList(items=items)


@router.get('/search', response_model=ChannelSearchList)
async def search_channels_endpoint(
    q: str,
    limit: int = 10,
    telegram: TelegramService = Depends(get_telegram),
):
    query = q.strip()
    if not query:
        raise ValidationError('Search query is required')

    items = await telegram.search_channels(query, limit=limit)
    return ChannelSearchList(items=items)


@router.post('', response_model=ChannelRead, status_code=status.HTTP_201_CREATED)
async def create_channel(
    payload: ChannelCreate,
    storage: Storage = Depends(get_storage),
    telegram: TelegramService = Depends(get_telegram),
):
    username = normalize_username(payload.username)
    if not username:
        raise ValidationError('Channel username is required')

    resolved = await telegram.resolve_channel(username)
    if not resolved or resolved.get('id') is None:
        raise ValidationError('Unable to resolve Telegram channel id')

    channel_id = resolved['id']
    username = resolved.get('username', username)
    title = resolved.get('title') or username or str(channel_id)

    existing = await storage.channels.get_by_id(int(channel_id))
    if existing:
        raise ConflictError('Channel already exists')

    if username:
        existing = await get_channel_by_username(storage, username)
        if existing:
            raise ConflictError('Channel already exists')

    channel = await storage.channels.create(
        channel_id=int(channel_id),
        username=username,
        title=title,
    )

    await log_channel_event(
        'created',
        {
            'id': channel['id'],
            'username': channel['username'],
            'title': channel['title'],
        },
    )

    return channel


@router.post('/import', response_model=ChannelImportSummary)
async def import_channels_from_dialogs(
    storage: Storage = Depends(get_storage),
    telegram: TelegramService = Depends(get_telegram),
):
    dialogs = await telegram.list_dialog_channels()
    if not dialogs:
        return ChannelImportSummary(total_found=0, created=0, skipped=0)

    deduped = {int(channel['id']): channel for channel in dialogs if channel.get('id') is not None}
    dialog_channels = list(deduped.values())
    if not dialog_channels:
        return ChannelImportSummary(total_found=0, created=0, skipped=0)
    channel_ids = list(deduped.keys())
    existing_ids: set[int] = set()
    if channel_ids:
        existing = await storage.channels.list_by_ids(channel_ids)
        existing_ids = {int(item['id']) for item in existing}

    usernames = [channel['username'] for channel in dialog_channels if channel.get('username')]
    existing_usernames: set[str] = set()
    if usernames:
        existing_by_username = await storage.channels.list_by_usernames(usernames)
        existing_usernames = {item['username'] for item in existing_by_username if item.get('username')}

    created_count = 0
    skipped_count = 0

    for channel in dialog_channels:
        channel_id = int(channel['id'])
        username = channel.get('username')
        title = channel.get('title') or username or str(channel_id)

        if channel_id in existing_ids or (username and username in existing_usernames):
            skipped_count += 1
            continue

        try:
            created = await storage.channels.create(
                channel_id=channel_id,
                username=username,
                title=title,
            )
        except Exception as exc:
            logger.warning('Failed to import channel %s: %s', channel_id, exc)
            skipped_count += 1
            continue

        created_count += 1
        await log_channel_event(
            'imported',
            {
                'id': created['id'],
                'username': created['username'],
                'title': created['title'],
            },
        )

    return ChannelImportSummary(
        total_found=len(dialog_channels),
        created=created_count,
        skipped=skipped_count,
    )


@router.delete('/{channel_id}')
async def delete_channel(
    channel_id: int,
    storage: Storage = Depends(get_storage),
):
    channel = await storage.channels.delete(channel_id)
    if channel is None:
        raise NotFoundError('Channel not found')

    await log_channel_event(
        'deleted',
        {
            'id': channel['id'],
            'username': channel['username'],
            'title': channel['title'],
        },
    )

    return {'status': 'deleted', 'id': channel_id}
