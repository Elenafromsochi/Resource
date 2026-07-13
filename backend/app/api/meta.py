"""Справочные эндпоинты (не требуют авторизации)."""

from __future__ import annotations

from fastapi import APIRouter

from ..config import settings
from ..questions import QUESTIONS

router = APIRouter(tags=["meta"])


@router.get("/questions")
def questions() -> dict:
    """Список вопросов про ресурсы для заполнения кабинета."""
    return {"questions": QUESTIONS}


@router.get("/config")
def config() -> dict:
    """Публичные настройки для клиента (какие кнопки входа показывать)."""
    return {"yandex_login": settings.yandex_login_enabled}
