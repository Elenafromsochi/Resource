from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class ChannelCreate(BaseModel):
    username: str = Field(
        ...,
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


class ChannelImportSummary(BaseModel):
    total_found: int
    created: int
    skipped: int


class HashtagCreate(BaseModel):
    tag: str = Field(...)


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


class PromptCreate(BaseModel):
    name: str = Field(...)
    content: str = Field(...)


class PromptUpdate(BaseModel):
    name: str | None = None
    content: str | None = None


class PromptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    content: str
    created_at: datetime | None
    updated_at: datetime | None


class PromptList(BaseModel):
    items: list[PromptRead]


class HashtagFrequency(BaseModel):
    tag: str
    count: int
    in_db: bool


class HashtagAnalysisRequest(BaseModel):
    prompt_id: int
    start_date: datetime
    end_date: datetime
    channel_ids: list[int] | None = None
    max_messages_per_channel: int | None = None


class HashtagAnalysisResponse(BaseModel):
    prompt_id: int
    start_date: datetime
    end_date: datetime
    channels: list[int]
    total_messages: int
    hashtags: list[HashtagFrequency]


class ParticipantChannel(BaseModel):
    id: int
    username: str | None
    title: str | None


class ParticipantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    display_name: str | None
    about: str | None
    photo_url: str | None
    channels: list[ParticipantChannel] = Field(default_factory=list)


class ParticipantList(BaseModel):
    items: list[ParticipantRead]
    total: int
    limit: int
    offset: int
