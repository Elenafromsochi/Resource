"""Pydantic-схемы запросов/ответов."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# --- Авторизация ---
class RegisterIn(BaseModel):
    username: str
    password: str
    display_name: str = ""


class LoginIn(BaseModel):
    username: str
    password: str


class TelegramAuthIn(BaseModel):
    init_data: str  # сырая строка Telegram WebApp.initData


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProfileOut(BaseModel):
    id: str
    username: str | None
    display_name: str
    auth_provider: str
    level: str
    trust_capital: float
    give_count: int
    ask_count: int
    on_vacation: bool

    class Config:
        from_attributes = True


# --- Ресурс / Потребность ---
class ListingIn(BaseModel):
    category: str
    title: str
    description: str = ""
    location: str | None = None
    fields: dict = Field(default_factory=dict)


class ResourceIn(ListingIn):
    ideal_for: str = ""


class ResourceOut(BaseModel):
    id: str
    owner_id: str
    category: str
    title: str
    description: str
    location: str | None
    fields: dict
    ideal_for: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class NeedOut(BaseModel):
    id: str
    owner_id: str
    category: str
    title: str
    description: str
    location: str | None
    fields: dict
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# --- ИИ-уточнения ---
class ClarifyIn(BaseModel):
    category: str
    side: str = "give"  # give|ask
    fields: dict = Field(default_factory=dict)


# --- Мэтчинг ---
class MatchOut(BaseModel):
    resource_id: str
    need_id: str
    score: float
    is_match: bool


# --- Сделка / договор ---
class DealCreateIn(BaseModel):
    resource_id: str | None = None
    need_id: str | None = None
    counterparty_id: str


class MessageIn(BaseModel):
    text: str


class ContractUpdateIn(BaseModel):
    updates: dict


# --- Отзыв STAR ---
class ReviewIn(BaseModel):
    situation: str = ""
    task: str = ""
    action: str = ""
    result: str = ""
    rating: int = 5
