from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select

from db import get_session
from models.user import User

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    session_factory = get_session()
    async with session_factory() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
        if not user:
            user = User(telegram_id=message.from_user.id)
            session.add(user)
            await session.commit()
    await message.answer(
        "Добро пожаловать в кооператив «РЕСУРС»!\n"
        "Команды: /add_resource, /add_need, /my_balance"
    )


@router.message(Command("my_balance"))
async def cmd_balance(message: Message) -> None:
    session_factory = get_session()
    async with session_factory() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
        if not user:
            await message.answer("Сначала выполните /start.")
            return
        await message.answer(
            "Ваш баланс:\n"
            f"Рейтинг: {user.rating_score:.2f}\n"
            f"Подарено: {user.gifts_given}\n"
            f"Получено: {user.gifts_received}\n"
            f"Баланс: {user.gift_balance}"
        )
