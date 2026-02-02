from __future__ import annotations

from fastapi import Request

from app.storage import Storage


def get_storage(request: Request) -> Storage:
    return request.app.state.storage
