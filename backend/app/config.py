from __future__ import annotations

from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "tg-channel-manager"
    api_prefix: str = "/api"

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@postgres:5432/app",
        alias="DATABASE_URL",
    )
    mongo_url: str = Field(default="mongodb://mongo:27017", alias="MONGO_URL")
    mongo_db: str = Field(default="app", alias="MONGO_DB")

    telegram_api_id: Optional[int] = Field(default=None, alias="TELEGRAM_API_ID")
    telegram_api_hash: Optional[str] = Field(default=None, alias="TELEGRAM_API_HASH")
    telegram_bot_token: Optional[str] = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telethon_session: str = Field(default="telethon", alias="TELETHON_SESSION")

    deepseek_api_key: Optional[str] = Field(default=None, alias="DEEPSEEK_API_KEY")
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com", alias="DEEPSEEK_BASE_URL"
    )

    cors_origins: List[str] = Field(
        default=["http://localhost:5173"], alias="CORS_ORIGINS"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: object) -> List[str]:
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return ["http://localhost:5173"]

    @field_validator(
        "telegram_api_id",
        "telegram_api_hash",
        "telegram_bot_token",
        "deepseek_api_key",
        mode="before",
    )
    @classmethod
    def empty_string_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


settings = Settings()
