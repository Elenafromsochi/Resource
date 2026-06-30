"""Точка входа FastAPI «Ресурс»: регистрация и ИИ-кабинет."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import auth, profile
from .config import settings
from .db import init_db


def create_app() -> FastAPI:
    app = FastAPI(title="Ресурс", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def _startup() -> None:
        init_db()

    @app.get("/api/health", tags=["health"])
    def health() -> dict:
        return {"status": "ok", "service": "resurs"}

    for module in (auth, profile):
        app.include_router(module.router, prefix="/api")

    return app


app = create_app()
