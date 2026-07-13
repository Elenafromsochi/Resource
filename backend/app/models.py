"""Модели данных: пользователь и его личный кабинет (профиль)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String, default="")  # пусто у входа через Яндекс
    yandex_id: Mapped[str | None] = mapped_column(String, index=True, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    profile: Mapped["Profile"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class Profile(Base):
    """Личный кабинет. Заполняется вручную или с помощью ИИ-помощника."""

    __tablename__ = "profiles"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    full_name: Mapped[str] = mapped_column(String, default="")
    avatar: Mapped[str] = mapped_column(Text, default="")  # фото профиля (data URL)
    occupation: Mapped[str] = mapped_column(String, default="")  # род занятий
    city: Mapped[str] = mapped_column(String, default="")
    about: Mapped[str] = mapped_column(Text, default="")  # о себе
    skills: Mapped[list] = mapped_column(JSON, default=list)  # навыки
    interests: Mapped[list] = mapped_column(JSON, default=list)  # интересы
    goals: Mapped[str] = mapped_column(Text, default="")  # что ищу / цели
    contacts: Mapped[str] = mapped_column(String, default="")
    answers: Mapped[dict] = mapped_column(JSON, default=dict)  # ответы на вопросы про ресурсы
    # Список карточек «Даю/Прошу»: у каждой свои поля (условия, время, формат, для кого).
    resources: Mapped[list] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    user: Mapped["User"] = relationship(back_populates="profile")
