from __future__ import annotations

from dataclasses import dataclass
import os
from typing import List
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


def _get_env(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None or value == '':
        return default
    return value


def _get_optional(name: str) -> Optional[str]:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    return value


def _get_int(name: str) -> Optional[int]:
    value = _get_optional(name)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _get_list(name: str, default: List[str]) -> List[str]:
    value = _get_optional(name)
    if value is None:
        return default
    return [item.strip() for item in value.split(',') if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str = 'tg-channel-manager'
    api_prefix: str = '/api'
    postgres_url: str = _get_env(
        'POSTGRES_URL',
        'postgresql+asyncpg://postgres:postgres@postgres:5432/app',
    )
    mongo_url: str = _get_env('MONGO_URL', 'mongodb://mongo:27017')
    mongo_db: str = _get_env('MONGO_DB', 'app')
    telegram_api_id: Optional[int] = _get_int('TELEGRAM_API_ID')
    telegram_api_hash: Optional[str] = _get_optional('TELEGRAM_API_HASH')
    telegram_bot_token: Optional[str] = _get_optional('TELEGRAM_BOT_TOKEN')
    telethon_session: str = _get_env('TELETHON_SESSION', 'telethon')
    deepseek_api_key: Optional[str] = _get_optional('DEEPSEEK_API_KEY')
    deepseek_base_url: str = _get_env(
        'DEEPSEEK_BASE_URL',
        'https://api.deepseek.com',
    )
    cors_origins: List[str] = _get_list(
        'CORS_ORIGINS',
        ['http://localhost:5173'],
    )


settings = Settings()
