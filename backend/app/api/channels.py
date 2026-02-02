from __future__ import annotations

import re
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from app.api.dependencies import get_storage
from app.schemas import ChannelCreate
from app.schemas import ChannelList
from app.schemas import ChannelRead
from app.schemas import ChannelSearchList
from app.storage import Storage
from app.storage.mongo import log_channel_event
from app.telethon_service import resolve_channel
from app.telethon_service import search_channels

router = APIRouter(prefix='/channels', tags=['channels'])


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
):
    query = q.strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='Search query is required',
        )

    items = await search_channels(query, limit=limit)
    return ChannelSearchList(items=items)


@router.post('', response_model=ChannelRead, status_code=status.HTTP_201_CREATED)
async def create_channel(
    payload: ChannelCreate,
    storage: Storage = Depends(get_storage),
):
    username = normalize_username(payload.username)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='Channel username is required',
        )

    resolved = await resolve_channel(username)
    if not resolved or resolved.get('id') is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='Unable to resolve Telegram channel id',
        )

    channel_id = resolved['id']
    username = resolved.get('username', username)
    title = resolved.get('title') or username or str(channel_id)

    existing = await storage.channels.get_by_id(int(channel_id))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Channel already exists',
        )

    if username:
        existing = await get_channel_by_username(storage, username)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='Channel already exists',
            )

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


@router.delete('/{channel_id}', status_code=status.HTTP_200_OK)
async def delete_channel(
    channel_id: int,
    storage: Storage = Depends(get_storage),
):
    channel = await storage.channels.delete(channel_id)
    if channel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Channel not found',
        )

    await log_channel_event(
        'deleted',
        {
            'id': channel['id'],
            'username': channel['username'],
            'title': channel['title'],
        },
    )

    return {'status': 'deleted', 'id': channel_id}
