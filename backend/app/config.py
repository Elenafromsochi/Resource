import os


APP_NAME = 'tg-channel-manager'
API_PREFIX = '/api'

POSTGRES_URL = os.environ['POSTGRES_URL']

MONGO_URL = os.environ['MONGO_URL']
MONGO_DB = os.environ['MONGO_DB']

TELEGRAM_API_ID = os.environ['TELEGRAM_API_ID']
TELEGRAM_API_HASH = os.environ['TELEGRAM_API_HASH']

TELETHON_SESSION = os.environ['TELETHON_SESSION']

DEEPSEEK_API_KEY = os.environ['DEEPSEEK_API_KEY']
DEEPSEEK_BASE_URL = 'https://api.deepseek.com'

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        'CORS_ORIGINS',
        'http://localhost:5173,http://127.0.0.1:5173',
    ).split(',')
    if origin.strip()
]
CORS_ORIGIN_REGEX = os.getenv(
    'CORS_ORIGIN_REGEX',
    r'^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?$',
)
