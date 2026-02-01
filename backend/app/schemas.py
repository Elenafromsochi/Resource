from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class ChannelCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=255)
    name: str | None = Field(default=None, max_length=255)


class ChannelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tg_peer_id: int | None
    username: str | None
    name: str
    dialog_type: str
    created_at: datetime


class ChannelList(BaseModel):
    items: list[ChannelRead]


class ChannelSyncResult(BaseModel):
    total: int
    created: int
    updated: int
    skipped: int
