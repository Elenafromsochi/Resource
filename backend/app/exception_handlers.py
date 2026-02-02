from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import INTERNAL_ERROR_MESSAGE
from app.exceptions import AppError


logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={'detail': exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(request: Request, exc: RequestValidationError):
        logger.warning('Request validation failed: %s', exc)
        return JSONResponse(
            status_code=422,
            content={'detail': exc.errors()},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception('Unhandled error: %s', exc)
        return JSONResponse(
            status_code=500,
            content={'detail': INTERNAL_ERROR_MESSAGE},
        )
