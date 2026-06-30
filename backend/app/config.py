"""Настройки сервиса. Читаются из переменных окружения."""

from __future__ import annotations

import os


class Settings:
    # БД: по умолчанию SQLite (локальный запуск/тесты), в docker — Postgres.
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./resurs.db")

    # Секрет для подписи JWT сайта.
    jwt_secret: str = os.getenv("JWT_SECRET", "dev-secret-change-me")
    jwt_ttl_seconds: int = int(os.getenv("JWT_TTL_SECONDS", str(7 * 24 * 3600)))

    # Токен Telegram-бота — для проверки initData мини-аппа.
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

    # Порог мэтча по умолчанию (поднимаемый).
    match_threshold: float = float(os.getenv("MATCH_THRESHOLD", "40"))

    # CORS: список origin сайта и мини-аппа.
    cors_origins: list[str] = [
        o.strip()
        for o in os.getenv("CORS_ORIGINS", "*").split(",")
        if o.strip()
    ]


settings = Settings()
