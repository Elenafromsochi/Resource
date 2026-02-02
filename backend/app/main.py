from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Optional
import re

from fastapi import Depends
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi import status
from fastapi.middleware.cors import CORSMiddleware

from app.config import API_PREFIX
from app.config import APP_NAME
from app.config import POSTGRES_URL
from app.migration_runner import apply_migrations
from app.mongo import log_channel_event
from app.mongo import ping_mongo
from app.schemas import ChannelCreate
from app.schemas import ChannelList
from app.schemas import ChannelRead
from app.storage import Storage
from app.telethon_service import resolve_channel


@asynccontextmanager
async def lifespan(app: FastAPI):
    storage = await Storage.create(POSTGRES_URL)
    await apply_migrations(storage.db)
    app.state.storage = storage
    yield
    await storage.close()


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


def get_storage(request: Request) -> Storage:
    return request.app.state.storage


async def get_channel_by_username(
    storage: Storage,
    username: str,
) -> Optional[dict]:
    return await storage.channels.get_by_username(username)


@app.get('/health')
async def healthcheck(storage: Storage = Depends(get_storage)):
    db_ok = True
    try:
        await storage.db.execute('SELECT 1')
    except Exception:  # pragma: no cover - best effort
        db_ok = False

    mongo_ok = await ping_mongo()
    return {'postgres': db_ok, 'mongo': mongo_ok}


@app.get(
    '/channels',
    response_model=ChannelList,
)
async def list_channels(
    storage: Storage = Depends(get_storage),
):
    items = await storage.channels.list()
    return ChannelList(items=items)


@app.post(
    '/channels',
    response_model=ChannelRead,
    status_code=status.HTTP_201_CREATED,
)
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
    if resolved:
        username = resolved.get('username', username)

    existing = await get_channel_by_username(storage, username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Channel already exists',
        )

    name = payload.name or (resolved.get('name') if resolved else None) or username

    channel = await storage.channels.create(username=username, name=name)

    await log_channel_event(
        'created',
        {'id': channel['id'], 'username': channel['username'], 'name': channel['name']},
    )

    return channel


@app.delete(
    '/channels/{channel_id}',
    status_code=status.HTTP_200_OK,
)
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
        {'id': channel['id'], 'username': channel['username'], 'name': channel['name']},
    )

    return {'status': 'deleted', 'id': channel_id}
