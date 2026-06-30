"""Точка входа FastAPI «Ресурс». Один бэкенд для сайта и Telegram Mini App."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import init_db
from .api import auth, deals, listings, matches


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

    for module in (auth, listings, matches, deals):
        app.include_router(module.router, prefix="/api")

    return app


app = create_app()
