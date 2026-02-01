from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class Settings:
    bot_token: str
    database_url: str
    redis_url: str
    openai_api_key: str | None
    min_balance_for_need: int
    match_threshold: int
    gpt_model: str
    whisper_model: str


def _get_env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def load_settings() -> Settings:
    return Settings(
        bot_token=_get_env("BOT_TOKEN"),
        database_url=_get_env("DATABASE_URL"),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        min_balance_for_need=int(os.getenv("MIN_BALANCE_FOR_NEED", "0")),
        match_threshold=int(os.getenv("MATCH_THRESHOLD", "80")),
        gpt_model=os.getenv("OPENAI_GPT_MODEL", "gpt-4o-mini"),
        whisper_model=os.getenv("OPENAI_WHISPER_MODEL", "whisper-1"),
    )
