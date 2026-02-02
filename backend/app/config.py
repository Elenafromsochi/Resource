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

HASHTAG_PREFIX = '#'

POSTGRES_URL = os.environ['POSTGRES_URL']

MONGO_URL = os.environ['MONGO_URL']
MONGO_DB = os.environ['MONGO_DB']

TELEGRAM_API_ID = os.environ['TELEGRAM_API_ID']
TELEGRAM_API_HASH = os.environ['TELEGRAM_API_HASH']

TELETHON_SESSION = os.environ['TELETHON_SESSION']

DEEPSEEK_API_KEY = os.environ['DEEPSEEK_API_KEY']
DEEPSEEK_BASE_URL = 'https://api.deepseek.com/v1'
DEEPSEEK_MODEL = 'deepseek-chat'
DEEPSEEK_MAX_TOTAL_TOKENS = 128000
DEEPSEEK_MAX_OUTPUT_TOKENS = 8000
DEEPSEEK_MAX_INPUT_TOKENS = 120000
DEEPSEEK_TEMPERATURE = 0.1
DEEPSEEK_TIMEOUT_SECONDS = 30

TOKEN_ESTIMATE_CHARS = 4

ANALYSIS_SYSTEM_PROMPT = (
    'Ты анализируешь сообщения из Telegram-каналов. '
    'Следуй инструкции из блока ИНСТРУКЦИЯ. '
    'Существующие хэштеги используй как подсказки, но можешь предлагать новые. '
    'Считай хэштеги только по предоставленным сообщениям. '
    'Ответ строго в JSON: {"hashtags":[{"tag":"#пример","count":3}]}'
)
ANALYSIS_PROMPT_TEMPLATE = (
    'ИНСТРУКЦИЯ:\n{prompt}\n\n'
    'СУЩЕСТВУЮЩИЕ_ХЭШТЕГИ:\n{hashtags}\n\n'
    'СООБЩЕНИЯ:\n'
)

INTERNAL_ERROR_MESSAGE = 'Внутренняя ошибка сервера'

MIGRATIONS_DIR = Path(__file__).resolve().parent / 'storage' / 'migrations'

