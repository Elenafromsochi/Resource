# Telegram MVP: Кооператив «РЕСУРС»

MVP Telegram-бот для взаимного обмена паями (ресурсами и потребностями) с ИИ-навигатором.

## Запуск

1. Установить зависимости:

```
pip install -r requirements.txt
```

2. Заполнить `.env`:

```
BOT_TOKEN=...
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/resource
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=...
```

Дополнительно:

- `MIN_BALANCE_FOR_NEED` (по умолчанию 0)
- `MATCH_THRESHOLD` (по умолчанию 80)
- `OPENAI_GPT_MODEL` (по умолчанию gpt-4o-mini)
- `OPENAI_WHISPER_MODEL` (по умолчанию whisper-1)
- `OPENAI_DALLE_MODEL` (по умолчанию dall-e-3)

3. Запустить:

```
python bot.py
```

## Docker Compose

1. Заполните `.env` (BOT_TOKEN, OPENAI_API_KEY и др.).
2. Запустите:

```
docker compose up --build
```

## Команды

- `/start` — регистрация.
- `/add_resource` — добавить ресурс (FSM: Что → Когда → Где).
- `/add_need` — добавить потребность (с проверкой баланса).
- `/my_balance` — баланс и рейтинг.
- `/chat_exit` — выйти из чата сделки.
