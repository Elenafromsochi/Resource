from __future__ import annotations

from fastapi import status

from app.config import INTERNAL_ERROR_MESSAGE


class AppError(Exception):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = INTERNAL_ERROR_MESSAGE

    def __init__(self, detail: str | None = None) -> None:
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)


class ValidationError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT


class ExternalServiceError(AppError):
    status_code = status.HTTP_502_BAD_GATEWAY
