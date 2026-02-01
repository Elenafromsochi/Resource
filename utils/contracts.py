from __future__ import annotations

from datetime import datetime

from models.deal import Deal
from models.resource import Resource
from models.need import Need
from models.user import User


def generate_contract(
    deal: Deal,
    resource: Resource,
    need: Need,
    participant_a: User,
    participant_b: User,
) -> str:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    exchange_type = resource.exchange_type.value if resource.exchange_type else "не указан"
    return (
        "ДОГОВОР ВЗАИМНОГО ПАЕВОГО ОБМЕНА\n"
        f"Дата составления: {now}\n\n"
        "Стороны:\n"
        f"Участник A (пайщик): Telegram ID {participant_a.telegram_id}\n"
        f"Участник B (пайщик): Telegram ID {participant_b.telegram_id}\n\n"
        "Предмет обмена:\n"
        f"Ресурс: {resource.description}\n"
        f"Категория: {resource.category or 'не указана'}\n"
        f"Формат: {resource.resource_type.value}\n"
        f"Условия: {exchange_type}\n"
        f"Когда: {resource.time_info or 'не указано'}\n"
        f"Где: {resource.location or 'не указано'}\n\n"
        "Потребность:\n"
        f"{need.description}\n"
        f"Категория: {need.category or 'не указана'}\n"
        f"Дедлайн: {need.deadline or 'не указан'}\n"
        f"Локация: {need.location or 'не указана'}\n\n"
        "Стороны подтверждают намерение выполнить обмен ресурсами/услугами "
        "в рамках кооператива «РЕСУРС».\n"
        "После взаимного подтверждения сделка переходит в этап передачи.\n"
    )
