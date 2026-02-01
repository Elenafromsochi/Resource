from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Optional
import re

from fastapi import Depends
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import API_PREFIX
from app.config import APP_NAME
from app.db import get_session
from app.db import init_db
from app.models import Channel
from app.mongo import log_channel_event
from app.mongo import ping_mongo
from app.schemas import ChannelCreate
from app.schemas import ChannelList
from app.schemas import ChannelRead
from app.schemas import ChannelSyncResult
from app.telethon_service import fetch_dialog_channels
from app.telethon_service import resolve_channel
from app.telethon_service import telethon_configured


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title=APP_NAME, root_path=API_PREFIX, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'http://localhost:5173',
        'http://127.0.0.1:5173',
    ],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


def normalize_username(raw: str) -> str:
    value = raw.strip()
    value = re.sub(r'^(https?://)?t\.me/', '', value, flags=re.IGNORECASE)
    value = re.sub(r'^(https?://)?telegram\.me/', '', value, flags=re.IGNORECASE)
    value = value.lstrip('@')
    return value.strip()


async def get_channel_by_username(
    session: AsyncSession,
    username: str,
) -> Optional[Channel]:
    result = await session.execute(
        select(Channel).where(Channel.username == username),
    )
    return result.scalar_one_or_none()


async def get_channel_by_peer_id(
    session: AsyncSession,
    tg_peer_id: int,
) -> Optional[Channel]:
    result = await session.execute(
        select(Channel).where(Channel.tg_peer_id == tg_peer_id),
    )
    return result.scalar_one_or_none()


@app.get('/health')
async def healthcheck(session: AsyncSession = Depends(get_session)):
    db_ok = True
    try:
        await session.execute(text('SELECT 1'))
    except Exception:  # pragma: no cover - best effort
        db_ok = False

    mongo_ok = await ping_mongo()
    return {'postgres': db_ok, 'mongo': mongo_ok}


@app.get(
    '/channels',
    response_model=ChannelList,
)
async def list_channels(
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Channel).order_by(Channel.created_at.desc()),
    )
    items = result.scalars().all()
    return ChannelList(items=items)


@app.post(
    '/channels',
    response_model=ChannelRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_channel(
    payload: ChannelCreate,
    session: AsyncSession = Depends(get_session),
):
    username = normalize_username(payload.username)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='Channel username is required',
        )

    resolved = await resolve_channel(username)
    if resolved:
        username = resolved.get('username', username)

    existing = await get_channel_by_username(session, username)
    if not existing and resolved and resolved.get('tg_peer_id') is not None:
        existing = await get_channel_by_peer_id(
            session,
            resolved['tg_peer_id'],
        )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Channel already exists',
        )

    name = payload.name or (resolved.get('name') if resolved else None) or username
    dialog_type = (resolved.get('dialog_type') if resolved else None) or 'channel'
    channel = Channel(
        tg_peer_id=resolved.get('tg_peer_id') if resolved else None,
        username=username,
        name=name,
        dialog_type=dialog_type,
    )
    session.add(channel)
    await session.commit()
    await session.refresh(channel)

    await log_channel_event(
        'created',
        {'id': channel.id, 'username': channel.username, 'name': channel.name},
    )

    return channel


@app.post(
    '/channels/sync',
    response_model=ChannelSyncResult,
    status_code=status.HTTP_200_OK,
)
async def sync_channels(
    session: AsyncSession = Depends(get_session),
):
    if not telethon_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Telethon is not configured',
        )

    dialogs = await fetch_dialog_channels()
    if not dialogs:
        return ChannelSyncResult(total=0, created=0, updated=0, skipped=0)

    peer_ids = {item['tg_peer_id'] for item in dialogs if item.get('tg_peer_id')}
    usernames = {item['username'] for item in dialogs if item.get('username')}

    existing_by_peer: dict[int, Channel] = {}
    if peer_ids:
        result = await session.execute(
            select(Channel).where(Channel.tg_peer_id.in_(peer_ids)),
        )
        existing_by_peer = {
            channel.tg_peer_id: channel for channel in result.scalars().all()
        }

    existing_by_username: dict[str, Channel] = {}
    if usernames:
        result = await session.execute(
            select(Channel).where(Channel.username.in_(usernames)),
        )
        existing_by_username = {
            channel.username: channel for channel in result.scalars().all()
        }

    created = 0
    updated = 0
    skipped = 0
    for entry in dialogs:
        peer_id = entry.get('tg_peer_id')
        username = entry.get('username')
        name = entry['name']
        dialog_type = entry['dialog_type']

        existing = existing_by_peer.get(peer_id) if peer_id else None
        if existing is None and username:
            existing = existing_by_username.get(username)

        if existing:
            changed = False
            if peer_id and existing.tg_peer_id != peer_id:
                existing.tg_peer_id = peer_id
                changed = True
            if username and existing.username != username:
                existing.username = username
                changed = True
            if existing.name != name:
                existing.name = name
                changed = True
            if existing.dialog_type != dialog_type:
                existing.dialog_type = dialog_type
                changed = True

            if changed:
                updated += 1
            else:
                skipped += 1
        else:
            channel = Channel(
                tg_peer_id=peer_id,
                username=username,
                name=name,
                dialog_type=dialog_type,
            )
            session.add(channel)
            created += 1

    if created or updated:
        await session.commit()
    else:
        await session.rollback()

    await log_channel_event(
        'synced',
        {
            'total': len(dialogs),
            'created': created,
            'updated': updated,
            'skipped': skipped,
        },
    )

    return ChannelSyncResult(
        total=len(dialogs),
        created=created,
        updated=updated,
        skipped=skipped,
    )


@app.delete(
    '/channels/{channel_id}',
    status_code=status.HTTP_200_OK,
)
async def delete_channel(
    channel_id: int,
    session: AsyncSession = Depends(get_session),
):
    channel = await session.get(Channel, channel_id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Channel not found',
        )

    await session.delete(channel)
    await session.commit()

    await log_channel_event(
        'deleted',
        {'id': channel.id, 'username': channel.username, 'name': channel.name},
    )

    return {'status': 'deleted', 'id': channel_id}
