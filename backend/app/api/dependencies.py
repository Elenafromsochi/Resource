from __future__ import annotations

from fastapi import Request

from app.deepseek import DeepSeek
from app.storage import Storage


def get_storage(request: Request) -> Storage:
    return request.app.state.storage


def get_deepseek(request: Request) -> DeepSeek:
    return request.app.state.deepseek
