"""Модели данных «Ресурса».

Перенос схемы «Подари» → «Ресурс» (см. бриф):
  gifts        → resources   (+ категория, условия, локация, поля под категорию)
  wishes       → needs        (полноценная зеркальная сущность)
  transactions → acts + contracts (акт отделён от договора; один акт = один договор)
  reviews      → reviews (STAR: s/t/a/r + коэффициент)
  profiles     → profiles (+ капитал доверия, уровень, баланс даю/прошу)
  matches      — новый
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.utcnow()


# Уровни профиля («Капитал доверия»).
LEVEL_LIGHT, LEVEL_MEDIUM, LEVEL_HIGH = "light", "medium", "high"


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    auth_provider: Mapped[str] = mapped_column(String, default="password")  # password|telegram|vk
    external_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    username: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    display_name: Mapped[str] = mapped_column(String, default="")
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)

    level: Mapped[str] = mapped_column(String, default=LEVEL_LIGHT)
    trust_capital: Mapped[float] = mapped_column(Float, default=50.0)  # 0..100
    # «Даю и прошу — два независимых акта». Баланс — мягкий индикатор, не блокировка.
    give_count: Mapped[int] = mapped_column(Integer, default=0)
    ask_count: Mapped[int] = mapped_column(Integer, default=0)
    on_vacation: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Resource(Base):
    """«Даю» — ресурс."""

    __tablename__ = "resources"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("profiles.id"), index=True)
    category: Mapped[str] = mapped_column(String, index=True)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text, default="")
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    fields: Mapped[dict] = mapped_column(JSON, default=dict)  # поля под категорию
    ideal_for: Mapped[str] = mapped_column(Text, default="")  # кому идеально подойдёт
    status: Mapped[str] = mapped_column(String, default="active")  # active|archived
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Need(Base):
    """«Прошу» — потребность. Зеркальна ресурсу: те же параметры."""

    __tablename__ = "needs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("profiles.id"), index=True)
    category: Mapped[str] = mapped_column(String, index=True)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text, default="")
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    fields: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Match(Base):
    """Результат зеркального мэтчинга ресурса и потребности."""

    __tablename__ = "matches"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    resource_id: Mapped[str] = mapped_column(ForeignKey("resources.id"), index=True)
    need_id: Mapped[str] = mapped_column(ForeignKey("needs.id"), index=True)
    score: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String, default="suggested")  # suggested|accepted|declined
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Deal(Base):
    """Чат сделки + живой Человеческий договор (хранится как JSON)."""

    __tablename__ = "deals"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    resource_id: Mapped[str | None] = mapped_column(ForeignKey("resources.id"), nullable=True)
    need_id: Mapped[str | None] = mapped_column(ForeignKey("needs.id"), nullable=True)
    giver_id: Mapped[str] = mapped_column(ForeignKey("profiles.id"), index=True)
    taker_id: Mapped[str] = mapped_column(ForeignKey("profiles.id"), index=True)
    status: Mapped[str] = mapped_column(String, default="open")  # open|signed|completed|disputed
    contract: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    messages: Mapped[list["Message"]] = relationship(
        back_populates="deal", cascade="all, delete-orphan", order_by="Message.created_at"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    deal_id: Mapped[str] = mapped_column(ForeignKey("deals.id"), index=True)
    role: Mapped[str] = mapped_column(String, default="user")  # user|bot_resurs|bot_mediator
    sender_id: Mapped[str | None] = mapped_column(String, nullable=True)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    deal: Mapped["Deal"] = relationship(back_populates="messages")


class Act(Base):
    """Акт передачи. Один акт = один договор (снимок на момент завершения)."""

    __tablename__ = "acts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    deal_id: Mapped[str] = mapped_column(ForeignKey("deals.id"), index=True)
    giver_id: Mapped[str] = mapped_column(ForeignKey("profiles.id"))
    taker_id: Mapped[str] = mapped_column(ForeignKey("profiles.id"))
    contract_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    completed_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Review(Base):
    """Отзыв по STAR (Ситуация/Задача/Действие/Результат) + коэффициент."""

    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    act_id: Mapped[str] = mapped_column(ForeignKey("acts.id"), index=True)
    author_id: Mapped[str] = mapped_column(ForeignKey("profiles.id"))
    subject_id: Mapped[str] = mapped_column(ForeignKey("profiles.id"), index=True)
    situation: Mapped[str] = mapped_column(Text, default="")
    task: Mapped[str] = mapped_column(Text, default="")
    action: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[str] = mapped_column(Text, default="")
    rating: Mapped[int] = mapped_column(Integer, default=5)  # 1..5
    coefficient: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
