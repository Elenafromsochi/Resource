"""Настройки сервиса. Читаются из переменных окружения."""

from __future__ import annotations

import os


class Settings:
    # БД: по умолчанию SQLite (локальный запуск/тесты), в docker — Postgres.
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./resurs.db")

    # Секрет для подписи JWT.
    jwt_secret: str = os.getenv("JWT_SECRET", "dev-secret-change-me")
    jwt_ttl_seconds: int = int(os.getenv("JWT_TTL_SECONDS", str(7 * 24 * 3600)))

    # ИИ-помощник кабинета. Если ключ есть — используется реальный Claude,
    # иначе — офлайн-заглушка с тем же интерфейсом.
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    ai_model: str = os.getenv("AI_MODEL", "claude-haiku-4-5-20251001")

    # CORS.
    cors_origins: list[str] = [
        o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()
    ]


settings = Settings()
