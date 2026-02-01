from __future__ import annotations

import re
from typing import Optional

from fastapi import Depends
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Query
from fastapi import status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import API_PREFIX
from app.config import APP_NAME
from app.config import CORS_ORIGINS
from app.config import DEEPSEEK_API_KEY
from app.db import get_session
from app.db import init_db
from app.deepseek import generate_summary
from app.models import Channel
from app.mongo import log_channel_event
from app.mongo import ping_mongo
from app.schemas import ChannelCreate
from app.schemas import ChannelList
from app.schemas import ChannelRead
from app.telethon_service import resolve_channel

app = FastAPI(title=APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.on_event('startup')
async def on_startup() -> None:
    await init_db()


def normalize_username(raw: str) -> str:
    value = raw.strip()
    value = re.sub(r'^(https?://)?t\.me/', '', value, flags=re.IGNORECASE)
    value = re.sub(r'^(https?://)?telegram\.me/', '', value, flags=re.IGNORECASE)
    value = value.lstrip('@')
    return value.strip()


async def get_channel_by_username(
    session: AsyncSession, username: str
) -> Optional[Channel]:
    result = await session.execute(
        select(Channel).where(Channel.username == username)
    )
    return result.scalar_one_or_none()


@app.get(f'{API_PREFIX}/health')
async def healthcheck(session: AsyncSession = Depends(get_session)):
    db_ok = True
    try:
        await session.execute(text('SELECT 1'))
    except Exception:  # pragma: no cover - best effort
        db_ok = False

    mongo_ok = await ping_mongo()
    return {'postgres': db_ok, 'mongo': mongo_ok}


@app.get(
    f'{API_PREFIX}/channels',
    response_model=ChannelList,
)
async def list_channels(
    include_summary: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Channel).order_by(Channel.created_at.desc())
    )
    items = result.scalars().all()

    summary = None
    if include_summary:
        if not DEEPSEEK_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='DeepSeek API key not configured',
            )
        names = ', '.join([channel.name for channel in items]) or 'No channels'
        summary = await generate_summary(names)

    return ChannelList(items=items, summary=summary)


@app.post(
    f'{API_PREFIX}/channels',
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

    existing = await get_channel_by_username(session, username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Channel already exists',
        )

    resolved = await resolve_channel(username)
    if resolved:
        username = resolved.get('username', username)

    existing = await get_channel_by_username(session, username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Channel already exists',
        )

    name = payload.name or (resolved.get('name') if resolved else None) or username

    channel = Channel(username=username, name=name)
    session.add(channel)
    await session.commit()
    await session.refresh(channel)

    await log_channel_event(
        'created',
        {'id': channel.id, 'username': channel.username, 'name': channel.name},
    )

    return channel


@app.delete(
    f'{API_PREFIX}/channels/{{channel_id}}',
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
