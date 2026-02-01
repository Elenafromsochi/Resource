from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChannelCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=255)
    name: str | None = Field(default=None, max_length=255)


class ChannelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    name: str
    created_at: datetime


class ChannelList(BaseModel):
    items: list[ChannelRead]
    summary: str | None = None
