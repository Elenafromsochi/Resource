import os
from pathlib import Path


APP_NAME = 'tg-channel-manager'
API_PREFIX = '/api'

CORS_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

CHANNEL_TITLE_MAX_LENGTH = 255
CHANNEL_USERNAME_MAX_LENGTH = 255
HASHTAG_MAX_LENGTH = 255
HASHTAG_PREFIX = '#'

POSTGRES_URL = os.environ['POSTGRES_URL']

MONGO_URL = os.environ['MONGO_URL']
MONGO_DB = os.environ['MONGO_DB']

TELEGRAM_API_ID = os.environ['TELEGRAM_API_ID']
TELEGRAM_API_HASH = os.environ['TELEGRAM_API_HASH']

TELETHON_SESSION = os.environ['TELETHON_SESSION']

MIGRATIONS_DIR = Path(__file__).resolve().parent / 'storage' / 'migrations'

