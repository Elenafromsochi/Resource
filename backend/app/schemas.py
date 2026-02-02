from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from app.config import CHANNEL_USERNAME_MAX_LENGTH
from app.config import HASHTAG_MAX_LENGTH


class ChannelCreate(BaseModel):
    username: str = Field(
        ...,
        min_length=2,
        max_length=CHANNEL_USERNAME_MAX_LENGTH,
    )


class ChannelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str | None
    title: str | None
    created_at: datetime | None


class ChannelList(BaseModel):
    items: list[ChannelRead]


class ChannelSearchItem(BaseModel):
    id: int
    username: str | None
    title: str | None
    description: str | None


class ChannelSearchList(BaseModel):
    items: list[ChannelSearchItem]


class HashtagCreate(BaseModel):
    tag: str = Field(..., min_length=1, max_length=HASHTAG_MAX_LENGTH)


class HashtagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tag: str
    created_at: datetime | None


class HashtagList(BaseModel):
    items: list[HashtagRead]
    total: int
    limit: int
    offset: int
