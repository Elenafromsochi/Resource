from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import status

from app.api.dependencies import get_storage
from app.config import DEFAULT_PAGE_SIZE
from app.config import HASHTAG_MAX_LENGTH
from app.config import HASHTAG_PREFIX
from app.config import MAX_PAGE_SIZE
from app.schemas import HashtagCreate
from app.schemas import HashtagList
from app.schemas import HashtagRead
from app.storage import Storage

router = APIRouter(prefix="/hashtags", tags=["hashtags"])


def normalize_hashtag(raw: str) -> str:
    value = raw.strip()
    if not value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Hashtag is required",
        )

    if not value.startswith(HASHTAG_PREFIX):
        value = f"{HASHTAG_PREFIX}{value}"

    if any(char.isspace() for char in value):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Hashtag must not contain spaces",
        )

    value = value.lower()
    if len(value) > HASHTAG_MAX_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Hashtag is too long",
        )

    return value


@router.get("", response_model=HashtagList)
async def list_hashtags(
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    storage: Storage = Depends(get_storage),
):
    items, total = await storage.hashtags.list(limit=limit, offset=offset)
    return HashtagList(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=HashtagRead, status_code=status.HTTP_201_CREATED)
async def create_hashtag(
    payload: HashtagCreate,
    storage: Storage = Depends(get_storage),
):
    tag = normalize_hashtag(payload.tag)
    existing = await storage.hashtags.get_by_tag(tag)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Hashtag already exists",
        )

    hashtag = await storage.hashtags.create(tag=tag)
    return hashtag


@router.delete("/{hashtag_id}", status_code=status.HTTP_200_OK)
async def delete_hashtag(
    hashtag_id: int,
    storage: Storage = Depends(get_storage),
):
    hashtag = await storage.hashtags.delete(hashtag_id)
    if hashtag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hashtag not found",
        )

    return {"status": "deleted", "id": hashtag_id}
