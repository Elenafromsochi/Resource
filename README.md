# Telegram Channel Manager

Stack: Docker Compose, FastAPI, Vue.js, PostgreSQL, MongoDB, Telethon.

## Quick start

1. Copy environment variables:

```bash
cp .env.example .env
```

2. Start the project:

```bash
docker compose up --build
```

After startup:
- Frontend: http://localhost:5173
- Backend: http://localhost:8000

## Environment variables

All variables are in `.env.example` and loaded from `.env`.

## API

### GET /api/channels
Returns the channel list.

### POST /api/channels
Creates a channel.

```json
{
  "username": "@channel",
  "name": "Optional"
}
```

### POST /api/channels/sync
Syncs Telegram dialogs (channels and groups) into the database.

### DELETE /api/channels/{id}
Deletes a channel.
