# Telegram MVP: Кооператив «РЕСУРС»

MVP Telegram-бот для взаимного обмена паями (ресурсами и потребностями) с ИИ-навигатором.

## Запуск

1. Установить зависимости:

```
pip install -r requirements.txt
```

2. Установить переменные окружения:

```
export BOT_TOKEN="..."
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/resource"
export REDIS_URL="redis://localhost:6379/0"
export OPENAI_API_KEY="..."
```

Дополнительно:

- `MIN_BALANCE_FOR_NEED` (по умолчанию 0)
- `MATCH_THRESHOLD` (по умолчанию 80)
- `OPENAI_GPT_MODEL` (по умолчанию gpt-4o-mini)
- `OPENAI_WHISPER_MODEL` (по умолчанию whisper-1)

3. Запустить:

```
python bot.py
```

## Docker Compose

1. Скопируйте и заполните `.env` (используется только Docker Compose):

```
cp .env.example .env
```

2. Заполните значения (BOT_TOKEN, OPENAI_API_KEY и др.).
3. Запустите:

```
docker compose up --build
```

## Команды

- `/start` — регистрация.
- `/add_resource` — добавить ресурс (FSM: Что → Когда → Где).
- `/add_need` — добавить потребность (с проверкой баланса).
- `/my_balance` — баланс и рейтинг.
- `/chat_exit` — выйти из чата сделки.
