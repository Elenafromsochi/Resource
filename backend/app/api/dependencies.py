from __future__ import annotations

from fastapi import Request

from app.deepseek import DeepSeek
from app.storage import Storage
from app.telethon_service import TelegramService


def get_storage(request: Request) -> Storage:
    return request.app.state.storage


def get_deepseek(request: Request) -> DeepSeek:
    return request.app.state.deepseek


def get_telegram(request: Request) -> TelegramService:
    return request.app.state.telegram
