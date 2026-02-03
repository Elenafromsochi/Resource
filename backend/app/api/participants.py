from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query

from app.api.dependencies import get_storage
from app.config import DEFAULT_PAGE_SIZE
from app.config import MAX_PAGE_SIZE
from app.schemas import ParticipantList
from app.storage import Storage


router = APIRouter(prefix='/participants', tags=['participants'])


@router.get('', response_model=ParticipantList)
async def list_participants(
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    storage: Storage = Depends(get_storage),
):
    items, total = await storage.participants.list(limit=limit, offset=offset)
    return ParticipantList(items=items, total=total, limit=limit, offset=offset)
