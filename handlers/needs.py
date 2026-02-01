from __future__ import annotations

import re

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy import func, select

from config import Settings
from db import get_session
from handlers.deals import build_deal_create_keyboard
from models.enums import NeedStatus, ResourceStatus
from models.need import Need
from models.resource import Resource
from models.user import User
from services.match_engine import MatchEngine
from utils.validators import infer_exchange_type, infer_resource_type

router = Router()


class NeedStates(StatesGroup):
    what = State()
    when = State()
    where = State()


CATEGORY_RE = re.compile(r"(категория|category)\s*:\s*(.+)", re.IGNORECASE)


async def _get_or_create_user(session, telegram_id: int) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(telegram_id=telegram_id)
        session.add(user)
        await session.commit()
    return user


def _extract_category(text: str) -> str | None:
    match = CATEGORY_RE.search(text)
    if not match:
        return None
    return match.group(2).strip()


@router.message(Command("add_need"))
async def cmd_add_need(message: Message, state: FSMContext, settings: Settings) -> None:
    session_factory = get_session()
    async with session_factory() as session:
        user = await _get_or_create_user(session, message.from_user.id)
        result = await session.execute(
            select(func.count(Resource.id)).where(
                Resource.owner_id == user.id, Resource.status == ResourceStatus.ACTIVE
            )
        )
        active_resources = result.scalar_one()

        if active_resources == 0:
            await message.answer(
                "Нельзя публиковать потребность без активного ресурса. "
                "Добавьте ресурс через /add_resource."
            )
            return
        if user.gift_balance < settings.min_balance_for_need:
            await message.answer(
                "Ваш баланс недостаточен для публикации потребности. "
                f"Минимум: {settings.min_balance_for_need}."
            )
            return

    await state.clear()
    await state.set_state(NeedStates.what)
    await message.answer(
        "Добавляем потребность. Опишите, что вам нужно.\n"
        "Можно указать 'Категория: ...' в сообщении."
    )


@router.message(NeedStates.what, F.text)
async def need_what(message: Message, state: FSMContext) -> None:
    text = message.text or ""
    await state.update_data(
        description=text,
        category=_extract_category(text),
        exchange_type=infer_exchange_type(text),
        format_type=infer_resource_type(text),
    )
    await state.set_state(NeedStates.when)
    await message.answer("Когда нужен ресурс (дедлайн)?")


@router.message(NeedStates.when, F.text)
async def need_when(message: Message, state: FSMContext) -> None:
    await state.update_data(deadline=message.text)
    await state.set_state(NeedStates.where)
    await message.answer("Где нужен ресурс (локация)?")


@router.message(NeedStates.where, F.text)
async def need_where(
    message: Message,
    state: FSMContext,
    match_engine: MatchEngine,
) -> None:
    session_factory = get_session()
    async with session_factory() as session:
        user = await _get_or_create_user(session, message.from_user.id)
        data = await state.get_data()
        need = Need(
            owner_id=user.id,
            description=data["description"],
            category=data.get("category"),
            deadline=data.get("deadline"),
            location=message.text,
            conditions=None,
            format_type=data.get("format_type"),
            exchange_type=data.get("exchange_type"),
            status=NeedStatus.ACTIVE,
        )
        session.add(need)
        await session.commit()
        await state.clear()

        await match_engine.enqueue_match("need", need.id)

        # Immediate matching against active resources
        resources_result = await session.execute(
            select(Resource, User)
            .join(User, Resource.owner_id == User.id)
            .where(Resource.status == ResourceStatus.ACTIVE)
        )
        matches: list[tuple[int, int, str, int]] = []
        for resource, owner in resources_result.all():
            score = match_engine.score(resource, need)
            if score >= match_engine.threshold:
                matches.append(
                    (owner.telegram_id, resource.id, resource.description, score)
                )

    await message.answer("Потребность добавлена. Ищем совпадения по ресурсам...")

    for owner_tg, resource_id, resource_desc, score in matches:
        keyboard = build_deal_create_keyboard(resource_id, need.id)
        await message.bot.send_message(
            owner_tg,
            (
                "Найдено совпадение > 80%!\n"
                f"Потребность: {need.description}\n"
                f"Ресурс: {resource_desc}\n"
                f"Скор: {score}"
            ),
            reply_markup=keyboard,
        )
        await message.bot.send_message(
            message.from_user.id,
            (
                "Найдено совпадение > 80%!\n"
                f"Ресурс: {resource_desc}\n"
                f"Скор: {score}"
            ),
            reply_markup=keyboard,
        )
