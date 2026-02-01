from __future__ import annotations

from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy import select

from db import get_session
from handlers.deals import build_deal_create_keyboard
from models.enums import ExchangeType, NeedStatus, ResourceStatus, ResourceType
from models.need import Need
from models.resource import Resource
from models.user import User
from services.match_engine import MatchEngine
from services.openai_service import OpenAIService
from utils.validators import extract_link, infer_exchange_type, infer_resource_type

router = Router()


class ResourceStates(StatesGroup):
    what = State()
    when = State()
    where = State()


async def _get_or_create_user(session, telegram_id: int) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(telegram_id=telegram_id)
        session.add(user)
        await session.commit()
    return user


def _parse_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _parse_exchange_type(value: object) -> ExchangeType | None:
    if isinstance(value, str):
        value = value.strip().lower()
        for enum_value in ExchangeType:
            if enum_value.value == value:
                return enum_value
    return None


def _parse_resource_type(value: object) -> ResourceType | None:
    if isinstance(value, str):
        value = value.strip().lower()
        for enum_value in ResourceType:
            if enum_value.value == value:
                return enum_value
    return None


@router.message(Command("add_resource"))
async def cmd_add_resource(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(ResourceStates.what)
    await message.answer(
        "Добавляем ресурс. Опишите, что вы предлагаете.\n"
        "Можно отправить текст, голос, фото или ссылку."
    )


@router.message(ResourceStates.what, F.voice)
@router.message(ResourceStates.what, F.photo)
@router.message(ResourceStates.what, F.text)
async def resource_what(
    message: Message,
    state: FSMContext,
    openai: OpenAIService,
) -> None:
    text = message.text or message.caption or ""
    link = extract_link(text)
    photo_file_id = None
    if message.photo:
        photo_file_id = message.photo[-1].file_id

    if message.voice:
        voice_file = await message.bot.get_file(message.voice.file_id)
        buffer = await message.bot.download_file(voice_file.file_path)
        voice_text = await openai.transcribe_voice(buffer.read(), "voice.ogg")
        if voice_text:
            text = voice_text

    parsed = {}
    if text or link or photo_file_id:
        parsed = await openai.parse_resource_fields(
            text=text or "Без описания",
            has_photo=bool(photo_file_id),
            link=link,
        )

    await state.update_data(
        description=text or "Без описания",
        category=parsed.get("category"),
        condition=parsed.get("condition"),
        estimated_value=_parse_decimal(parsed.get("estimated_value")),
        exchange_type=_parse_exchange_type(parsed.get("exchange_type"))
        or infer_exchange_type(text),
        resource_type=_parse_resource_type(parsed.get("resource_type"))
        or infer_resource_type(text)
        or ResourceType.ITEM,
        photo_file_id=photo_file_id,
        link=link,
    )
    await state.set_state(ResourceStates.when)
    await message.answer("Когда ресурс доступен?")


@router.message(ResourceStates.when, F.text)
async def resource_when(message: Message, state: FSMContext) -> None:
    await state.update_data(time_info=message.text)
    await state.set_state(ResourceStates.where)
    await message.answer("Где ресурс доступен (локация)?")


@router.message(ResourceStates.where, F.text)
async def resource_where(
    message: Message,
    state: FSMContext,
    match_engine: MatchEngine,
) -> None:
    session_factory = get_session()
    async with session_factory() as session:
        user = await _get_or_create_user(session, message.from_user.id)
        data = await state.get_data()
        resource = Resource(
            owner_id=user.id,
            resource_type=data["resource_type"],
            description=data["description"],
            time_info=data.get("time_info"),
            location=message.text,
            category=data.get("category"),
            condition=data.get("condition"),
            estimated_value=data.get("estimated_value"),
            exchange_type=data.get("exchange_type"),
            photo_file_id=data.get("photo_file_id"),
            link=data.get("link"),
            status=ResourceStatus.ACTIVE,
        )
        session.add(resource)
        await session.commit()
        await state.clear()

        await match_engine.enqueue_match("resource", resource.id)

        needs_result = await session.execute(
            select(Need, User)
            .join(User, Need.owner_id == User.id)
            .where(Need.status == NeedStatus.ACTIVE)
        )
        matches: list[tuple[int, int, str, int]] = []
        for need, owner in needs_result.all():
            score = match_engine.score(resource, need)
            if score >= match_engine.threshold:
                matches.append((owner.telegram_id, need.id, need.description, score))

        resource_desc = resource.description
        resource_id = resource.id

    await message.answer("Ресурс добавлен. Ищем совпадения по потребностям...")

    for owner_tg, need_id, need_desc, score in matches:
        keyboard = build_deal_create_keyboard(resource_id, need_id)
        await message.bot.send_message(
            owner_tg,
            (
                "Найдено совпадение > 80%!\n"
                f"Потребность: {need_desc}\n"
                f"Ресурс: {resource_desc}\n"
                f"Скор: {score}"
            ),
            reply_markup=keyboard,
        )
        await message.bot.send_message(
            message.from_user.id,
            (
                "Найдено совпадение > 80%!\n"
                f"Потребность: {need_desc}\n"
                f"Скор: {score}"
            ),
            reply_markup=keyboard,
        )
