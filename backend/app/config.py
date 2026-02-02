import os


APP_NAME = 'tg-channel-manager'
API_PREFIX = '/api'

POSTGRES_URL = os.environ['POSTGRES_URL']
if POSTGRES_URL.startswith('postgresql+asyncpg://'):
    POSTGRES_URL = POSTGRES_URL.replace('postgresql+asyncpg://', 'postgresql://', 1)

MONGO_URL = os.environ['MONGO_URL']
MONGO_DB = os.environ['MONGO_DB']

TELEGRAM_API_ID = os.environ['TELEGRAM_API_ID']
TELEGRAM_API_HASH = os.environ['TELEGRAM_API_HASH']

TELETHON_SESSION = os.environ['TELETHON_SESSION']

