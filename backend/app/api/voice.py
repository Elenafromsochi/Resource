"""Голосовой ввод: человек говорит, сервис возвращает текст.

Точка входа для кнопки микрофона в кабинете. Аудио приходит файлом, обратно
уходит только распознанный текст — саму запись не храним и никуда не кладём:
она нужна ровно на время распознавания.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from ..auth import get_current_user
from ..models import User
from ..voice import MAX_AUDIO_BYTES, VoiceError, is_configured, transcribe

router = APIRouter(prefix="/voice", tags=["voice"])


@router.get("/status")
def voice_status(user: User = Depends(get_current_user)) -> dict:
    """Включён ли голосовой ввод. Кабинет по этому ответу прячет микрофон,
    если ключ не задан, — чтобы кнопка не обманывала."""
    return {"enabled": is_configured()}


@router.post("/transcribe")
async def voice_transcribe(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
) -> dict:
    """Запись → текст. Пустой текст означает тишину, а не ошибку."""
    audio = await file.read()

    # Проверяем размер и здесь: до распознавания, чтобы не тащить в память лишнее.
    if len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Запись слишком длинная. Скажите короче — одной репликой.",
        )

    try:
        text = transcribe(audio, file.content_type or "audio/webm")
    except VoiceError as err:
        # Текст ошибки писался для человека — отдаём его как есть.
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(err)) from err

    return {"text": text}
