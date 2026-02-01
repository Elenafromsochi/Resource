import os


APP_NAME = 'tg-channel-manager'
API_PREFIX = os.getenv('API_PREFIX', '/api')

POSTGRES_URL = os.environ['POSTGRES_URL']

MONGO_URL = os.environ['MONGO_URL']
MONGO_DB = os.environ['MONGO_DB']

TELEGRAM_API_ID = os.environ['TELEGRAM_API_ID']
TELEGRAM_API_HASH = os.environ['TELEGRAM_API_HASH']

TELETHON_SESSION = os.environ['TELETHON_SESSION']

DEEPSEEK_API_KEY = os.environ['DEEPSEEK_API_KEY']
DEEPSEEK_BASE_URL = os.environ['DEEPSEEK_BASE_URL']
