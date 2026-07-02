"""Справочные эндпоинты (не требуют авторизации)."""

from __future__ import annotations

from fastapi import APIRouter

from ..questions import QUESTIONS

router = APIRouter(tags=["meta"])


@router.get("/questions")
def questions() -> dict:
    """Список вопросов про ресурсы для заполнения кабинета."""
    return {"questions": QUESTIONS}
