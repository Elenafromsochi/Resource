"""Настройки сервиса. Читаются из переменных окружения."""

from __future__ import annotations

import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def _normalize_db_url(url: str) -> str:
    """Привести строку подключения к виду, понятному SQLAlchemy, и убрать
    зависимость от файла SSL-сертификата.

    1. Хостинги (в т.ч. Timeweb) выдают URL вида `postgres://...`, SQLAlchemy
       ожидает `postgresql://...`.
    2. Timeweb добавляет `sslmode=verify-full` и `sslrootcert=...`, что требует
       файла корневого сертификата внутри контейнера (его там нет — приложение
       падает при старте). Для прототипа переключаем на `sslmode=require`
       (соединение шифруется, но сертификат не проверяется) и убираем sslrootcert.
    """
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]

    if url.startswith("postgresql://"):
        parts = urlsplit(url)
        query = dict(parse_qsl(parts.query))
        if query.get("sslmode") in ("verify-full", "verify-ca"):
            query["sslmode"] = "require"
        query.pop("sslrootcert", None)
        url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))

    return url


class Settings:
    # БД: по умолчанию SQLite (локальный запуск/тесты), в docker — Postgres.
    database_url: str = _normalize_db_url(os.getenv("DATABASE_URL", "sqlite:///./resurs.db"))

    # Секрет для подписи JWT.
    jwt_secret: str = os.getenv("JWT_SECRET", "dev-secret-change-me")
    jwt_ttl_seconds: int = int(os.getenv("JWT_TTL_SECONDS", str(7 * 24 * 3600)))

    # ИИ-помощник кабинета. Если ключ есть — используется реальный Claude,
    # иначе — офлайн-заглушка с тем же интерфейсом.
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    ai_model: str = os.getenv("AI_MODEL", "claude-haiku-4-5-20251001")

    # YandexGPT (российский ИИ, работает с РФ-сервера без VPN).
    yandex_api_key: str = os.getenv("YANDEX_API_KEY", "")
    yandex_folder_id: str = os.getenv("YANDEX_FOLDER_ID", "")
    yandex_model: str = os.getenv("YANDEX_MODEL", "yandexgpt-lite")

    # Вход через Яндекс ID (OAuth). Если ключи заданы — на входе показывается
    # кнопка «Войти через Яндекс» (одно касание, без пароля).
    yandex_oauth_client_id: str = os.getenv("YANDEX_OAUTH_CLIENT_ID", "")
    yandex_oauth_client_secret: str = os.getenv("YANDEX_OAUTH_CLIENT_SECRET", "")
    # Публичный адрес сайта (для redirect_uri). Напр. https://resurs.example.ru
    # Должен точно совпадать с Redirect URI, указанным в приложении Яндекса.
    public_url: str = os.getenv("PUBLIC_URL", "").rstrip("/")

    @property
    def yandex_login_enabled(self) -> bool:
        return bool(self.yandex_oauth_client_id and self.yandex_oauth_client_secret)

    # CORS.
    cors_origins: list[str] = [
        o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()
    ]


settings = Settings()
