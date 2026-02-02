from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class ChannelCreate(BaseModel):
    username: str = Field(
        ...,
        min_length=2,
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
    tag: str = Field(..., min_length=1)


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
