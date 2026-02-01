from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from config import load_settings
from db import init_db
from handlers import deals, needs, registration, resources
from services.match_engine import MatchEngine
from services.openai_service import OpenAIService


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = load_settings()
    await init_db(settings.database_url)

    storage = RedisStorage.from_url(settings.redis_url)
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=storage)

    dp["settings"] = settings
    dp["openai"] = OpenAIService(
        api_key=settings.openai_api_key,
        gpt_model=settings.gpt_model,
        whisper_model=settings.whisper_model,
    )
    dp["match_engine"] = MatchEngine(
        redis_url=settings.redis_url,
        threshold=settings.match_threshold,
    )

    dp.include_router(registration.router)
    dp.include_router(resources.router)
    dp.include_router(needs.router)
    dp.include_router(deals.router)

    try:
        await dp.start_polling(bot)
    finally:
        await dp["openai"].close()
        await dp["match_engine"].close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
