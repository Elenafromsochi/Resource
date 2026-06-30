"""Точка входа FastAPI «Ресурс»: регистрация и ИИ-кабинет."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import auth, profile
from .config import settings
from .db import init_db

# Собранный фронт (если есть): backend/static. В Docker сюда кладётся сборка Vue,
# и один сервер отдаёт и API (/api/...), и сам сайт.
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


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

    # Отдаём собранный сайт с того же адреса (если сборка присутствует).
    if STATIC_DIR.is_dir():
        assets = STATIC_DIR / "assets"
        if assets.is_dir():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa(full_path: str) -> FileResponse:
            candidate = STATIC_DIR / full_path
            if full_path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()
