from __future__ import annotations

import re

from models.enums import ExchangeType, ResourceType


LINK_RE = re.compile(r"(https?://\S+)")


def extract_link(text: str | None) -> str | None:
    if not text:
        return None
    match = LINK_RE.search(text)
    return match.group(1) if match else None


def infer_exchange_type(text: str | None) -> ExchangeType | None:
    if not text:
        return None
    lowered = text.lower()
    if any(keyword in lowered for keyword in ["дар", "подар", "безвозмезд", "бесплат"]):
        return ExchangeType.GIFT
    if any(keyword in lowered for keyword in ["обмен", "бартер"]):
        return ExchangeType.BARTER
    if any(keyword in lowered for keyword in ["продам", "цена", "стоимость", "руб"]):
        return ExchangeType.MONEY
    return None


def infer_resource_type(text: str | None) -> ResourceType | None:
    if not text:
        return None
    lowered = text.lower()
    if any(keyword in lowered for keyword in ["услуг", "сделаю", "помогу"]):
        return ResourceType.SERVICE
    if any(keyword in lowered for keyword in ["опыт", "экскурс", "обуч"]):
        return ResourceType.EXPERIENCE
    if any(keyword in lowered for keyword in ["вещь", "товар", "предмет"]):
        return ResourceType.ITEM
    return None
