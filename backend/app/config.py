from __future__ import annotations

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


APP_NAME: str = 'tg-channel-manager'
API_PREFIX: str = '/api'
POSTGRES_URL: str = _get_env(
    'POSTGRES_URL',
    'postgresql+asyncpg://user:password@postgres:5432/db',
)
MONGO_URL: str = _get_env('MONGO_URL', 'mongodb://mongo:27017')
MONGO_DB: str = _get_env('MONGO_DB', 'app')
TELEGRAM_API_ID: Optional[int] = _get_int('TELEGRAM_API_ID')
TELEGRAM_API_HASH: Optional[str] = _get_optional('TELEGRAM_API_HASH')
TELEGRAM_BOT_TOKEN: Optional[str] = _get_optional('TELEGRAM_BOT_TOKEN')
TELETHON_SESSION: str = _get_env('TELETHON_SESSION', 'telethon')
DEEPSEEK_API_KEY: Optional[str] = _get_optional('DEEPSEEK_API_KEY')
DEEPSEEK_BASE_URL: str = _get_env(
    'DEEPSEEK_BASE_URL',
    'https://api.deepseek.com',
)
CORS_ORIGINS: List[str] = _get_list(
    'CORS_ORIGINS',
    ['http://localhost:5173'],
)
