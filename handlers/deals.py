from __future__ import annotations

from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select

from db import get_session
from models.deal import Deal
from models.enums import DealStatus, NeedStatus, ResourceStatus
from models.need import Need
from models.resource import Resource
from models.user import User
from utils.contracts import generate_contract
from utils.rating import apply_deal_completion

router = Router()


class DealChatStates(StatesGroup):
    active = State()


def build_deal_create_keyboard(resource_id: int, need_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Создать сделку",
                    callback_data=f"deal:create:{resource_id}:{need_id}",
                )
            ]
        ]
    )


def _build_sign_keyboard(deal_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Подписать", callback_data=f"deal:sign:{deal_id}")]
        ]
    )


def _build_transfer_keyboard(deal_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Передал ресурс", callback_data=f"deal:transfer:{deal_id}"
                ),
                InlineKeyboardButton(
                    text="Подтвердить получение",
                    callback_data=f"deal:confirm:{deal_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Открыть чат", callback_data=f"deal:chat:{deal_id}"
                )
            ],
        ]
    )


async def _get_or_create_user(session, telegram_id: int) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(telegram_id=telegram_id)
        session.add(user)
        await session.commit()
    return user


@router.callback_query(F.data.startswith("deal:create:"))
async def deal_create(callback: CallbackQuery) -> None:
    _, _, resource_id_str, need_id_str = callback.data.split(":")
    resource_id = int(resource_id_str)
    need_id = int(need_id_str)

    session_factory = get_session()
    async with session_factory() as session:
        resource = await session.get(Resource, resource_id)
        need = await session.get(Need, need_id)
        if not resource or not need:
            await callback.answer("Ресурс или потребность не найдены.", show_alert=True)
            return
        if resource.status != ResourceStatus.ACTIVE or need.status != NeedStatus.ACTIVE:
            await callback.answer("Сделка недоступна.", show_alert=True)
            return

        result = await session.execute(
            select(Deal).where(Deal.resource_id == resource_id, Deal.need_id == need_id)
        )
        deal = result.scalar_one_or_none()
        if not deal:
            deal = Deal(
                resource_id=resource_id,
                need_id=need_id,
                participant_a_id=resource.owner_id,
                participant_b_id=need.owner_id,
                status=DealStatus.DRAFT,
            )
            session.add(deal)
            await session.flush()

        participant_a = await session.get(User, resource.owner_id)
        participant_b = await session.get(User, need.owner_id)
        deal.contract_text = generate_contract(
            deal, resource, need, participant_a, participant_b
        )
        participant_a_tg = participant_a.telegram_id
        participant_b_tg = participant_b.telegram_id
        deal_id = deal.id
        contract_text = deal.contract_text
        await session.commit()

    await callback.message.answer(
        "Сделка создана. Договор отправлен обеим сторонам."
    )
    await callback.bot.send_message(
        participant_a_tg,
        contract_text,
        reply_markup=_build_sign_keyboard(deal_id),
    )
    await callback.bot.send_message(
        participant_b_tg,
        contract_text,
        reply_markup=_build_sign_keyboard(deal_id),
    )


@router.callback_query(F.data.startswith("deal:sign:"))
async def deal_sign(callback: CallbackQuery) -> None:
    deal_id = int(callback.data.split(":")[2])
    session_factory = get_session()
    async with session_factory() as session:
        deal = await session.get(Deal, deal_id)
        if not deal:
            await callback.answer("Сделка не найдена.", show_alert=True)
            return
        user = await _get_or_create_user(session, callback.from_user.id)
        if user.id == deal.participant_a_id:
            deal.signed_by_a = True
        elif user.id == deal.participant_b_id:
            deal.signed_by_b = True
        else:
            await callback.answer("Вы не участник сделки.", show_alert=True)
            return

        both_signed = deal.signed_by_a and deal.signed_by_b
        if both_signed:
            deal.status = DealStatus.SIGNED

        participant_a = await session.get(User, deal.participant_a_id)
        participant_b = await session.get(User, deal.participant_b_id)
        participant_a_tg = participant_a.telegram_id
        participant_b_tg = participant_b.telegram_id
        await session.commit()

    await callback.answer("Подпись зафиксирована.")
    if both_signed:
        await callback.bot.send_message(
            participant_a_tg,
            "Обе стороны подписали договор. Переход к передаче.",
            reply_markup=_build_transfer_keyboard(deal.id),
        )
        await callback.bot.send_message(
            participant_b_tg,
            "Обе стороны подписали договор. Переход к передаче.",
            reply_markup=_build_transfer_keyboard(deal.id),
        )


@router.callback_query(F.data.startswith("deal:transfer:"))
async def deal_transfer(callback: CallbackQuery) -> None:
    deal_id = int(callback.data.split(":")[2])
    session_factory = get_session()
    async with session_factory() as session:
        deal = await session.get(Deal, deal_id)
        if not deal:
            await callback.answer("Сделка не найдена.", show_alert=True)
            return
        user = await _get_or_create_user(session, callback.from_user.id)
        if user.id != deal.participant_a_id:
            await callback.answer("Передачу подтверждает участник A.", show_alert=True)
            return
        deal.transfer_by_a = True
        deal.status = DealStatus.TRANSFER
        participant_b = await session.get(User, deal.participant_b_id)
        participant_b_tg = participant_b.telegram_id
        await session.commit()

    await callback.answer("Передача зафиксирована.")
    await callback.bot.send_message(
        callback.from_user.id,
        "Ожидаем подтверждения получения от второй стороны.",
    )
    await callback.bot.send_message(
        participant_b_tg,
        "Участник A отметил передачу. Подтвердите получение.",
        reply_markup=_build_transfer_keyboard(deal.id),
    )


@router.callback_query(F.data.startswith("deal:confirm:"))
async def deal_confirm(callback: CallbackQuery) -> None:
    deal_id = int(callback.data.split(":")[2])
    session_factory = get_session()
    async with session_factory() as session:
        deal = await session.get(Deal, deal_id)
        if not deal:
            await callback.answer("Сделка не найдена.", show_alert=True)
            return
        user = await _get_or_create_user(session, callback.from_user.id)
        if user.id != deal.participant_b_id:
            await callback.answer("Подтверждение за участником B.", show_alert=True)
            return
        deal.transfer_by_b = True
        if deal.transfer_by_a:
            deal.status = DealStatus.COMPLETED

        resource = await session.get(Resource, deal.resource_id)
        need = await session.get(Need, deal.need_id)
        participant_a = await session.get(User, deal.participant_a_id)
        participant_b = await session.get(User, deal.participant_b_id)
        participant_a_tg = participant_a.telegram_id
        participant_b_tg = participant_b.telegram_id
        completed = deal.status == DealStatus.COMPLETED
        if completed:
            resource.status = ResourceStatus.ARCHIVED
            need.status = NeedStatus.ARCHIVED
            apply_deal_completion(participant_a, participant_b)
        await session.commit()

    await callback.answer("Получение подтверждено.")
    if completed:
        await callback.bot.send_message(
            participant_a_tg,
            "Сделка завершена. Рейтинг обновлен.",
        )
        await callback.bot.send_message(
            participant_b_tg,
            "Сделка завершена. Рейтинг обновлен.",
        )


@router.callback_query(F.data.startswith("deal:chat:"))
async def deal_chat_open(callback: CallbackQuery, state: FSMContext) -> None:
    deal_id = int(callback.data.split(":")[2])
    await state.set_state(DealChatStates.active)
    await state.update_data(deal_id=deal_id)
    await callback.answer("Чат открыт. Отправляйте сообщения.")


@router.message(DealChatStates.active, F.text)
async def deal_chat_message(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    deal_id = data.get("deal_id")
    if not deal_id:
        await message.answer("Чат не найден.")
        return

    session_factory = get_session()
    async with session_factory() as session:
        deal = await session.get(Deal, deal_id)
        if not deal:
            await message.answer("Сделка не найдена.")
            return
        user = await _get_or_create_user(session, message.from_user.id)
        if user.id not in (deal.participant_a_id, deal.participant_b_id):
            await message.answer("Вы не участник этой сделки.")
            return
        other_id = (
            deal.participant_b_id
            if user.id == deal.participant_a_id
            else deal.participant_a_id
        )
        other = await session.get(User, other_id)
        chat_entry = {
            "ts": datetime.utcnow().isoformat(),
            "from": user.telegram_id,
            "text": message.text,
        }
        history = list(deal.chat_history or [])
        history.append(chat_entry)
        deal.chat_history = history
        await session.commit()

    await message.bot.send_message(other.telegram_id, f"Сообщение по сделке: {message.text}")


@router.message(Command("chat_exit"))
async def deal_chat_exit(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Вы вышли из чата сделки.")
