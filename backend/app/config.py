import os

APP_NAME='tg-channel-manager'
API_PREFIX='/api'
POSTGRES_URL=os.getenv('POSTGRES_URL') or 'postgresql+asyncpg://user:password@postgres:5432/db'
MONGO_URL=os.getenv('MONGO_URL') or 'mongodb://mongo:27017'
MONGO_DB=os.getenv('MONGO_DB') or 'app'
_telegram_api_id_raw=os.getenv('TELEGRAM_API_ID','').strip()
try: TELEGRAM_API_ID=int(_telegram_api_id_raw) if _telegram_api_id_raw else None
except ValueError: TELEGRAM_API_ID=None
TELEGRAM_API_HASH=os.getenv('TELEGRAM_API_HASH','').strip() or None
TELETHON_SESSION=os.getenv('TELETHON_SESSION') or 'telethon'
DEEPSEEK_API_KEY=os.getenv('DEEPSEEK_API_KEY','').strip() or None
DEEPSEEK_BASE_URL=os.getenv('DEEPSEEK_BASE_URL') or 'https://api.deepseek.com'
