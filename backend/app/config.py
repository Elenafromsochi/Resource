from __future__ import annotations

import os
from typing import List
from typing import Optional

APP_NAME: str = 'tg-channel-manager'
API_PREFIX: str = '/api'

POSTGRES_URL: str = (
    os.getenv('POSTGRES_URL')
    or 'postgresql+asyncpg://user:password@postgres:5432/db'
)
MONGO_URL: str = os.getenv('MONGO_URL') or 'mongodb://mongo:27017'
MONGO_DB: str = os.getenv('MONGO_DB') or 'app'

_telegram_api_id_raw = os.getenv('TELEGRAM_API_ID', '').strip()
try:
    TELEGRAM_API_ID: Optional[int] = (
        int(_telegram_api_id_raw) if _telegram_api_id_raw else None
    )
except ValueError:
    TELEGRAM_API_ID = None

TELEGRAM_API_HASH: Optional[str] = (
    os.getenv('TELEGRAM_API_HASH', '').strip() or None
)
TELETHON_SESSION: str = os.getenv('TELETHON_SESSION') or 'telethon'

DEEPSEEK_API_KEY: Optional[str] = (
    os.getenv('DEEPSEEK_API_KEY', '').strip() or None
)
DEEPSEEK_BASE_URL: str = os.getenv('DEEPSEEK_BASE_URL') or (
    'https://api.deepseek.com'
)

_cors_origins_raw = os.getenv('CORS_ORIGINS', '').strip()
if _cors_origins_raw:
    CORS_ORIGINS: List[str] = [
        item.strip()
        for item in _cors_origins_raw.split(',')
        if item.strip()
    ]
else:
    CORS_ORIGINS = ['http://localhost:5173']
