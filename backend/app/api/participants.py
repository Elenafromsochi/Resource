from __future__ import annotations

import logging
from datetime import datetime
from datetime import timezone

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query

from app.api.dependencies import get_storage
from app.api.dependencies import get_telegram
from app.config import DEFAULT_PAGE_SIZE
from app.config import MAX_PAGE_SIZE
from app.exceptions import NotFoundError
from app.schemas import ParticipantList
from app.schemas import ParticipantRead
from app.storage import Storage
from app.telethon_service import TelegramService


router = APIRouter(prefix='/participants', tags=['participants'])
logger = logging.getLogger(__name__)


@router.get('', response_model=ParticipantList)
async def list_participants(
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    storage: Storage = Depends(get_storage),
):
    items, total = await storage.participants.list(limit=limit, offset=offset)
    return ParticipantList(items=items, total=total, limit=limit, offset=offset)


@router.get('/{user_id}', response_model=ParticipantRead)
async def get_participant(
    user_id: int,
    storage: Storage = Depends(get_storage),
    telegram: TelegramService = Depends(get_telegram),
):
    now = datetime.now(timezone.utc)
    try:
        profiles = await telegram.fetch_user_profiles([user_id])
    except Exception as exc:
        logger.warning('Failed to fetch participant %s: %s', user_id, exc)
        profiles = []

    if profiles:
        profile = profiles[0]
        profile['profile_updated_at'] = now
        profile['updated_at'] = now
        await storage.participants.upsert_details([profile])

    stored = await storage.participants.get_by_id(user_id)
    if not stored:
        raise NotFoundError('Participant not found')
    return stored
