"""Извлечение карточки ресурса/потребности из свободного рассказа.

Человек наговаривает всё одним текстом → ИИ раскладывает по полям карточки
(категория, короткое название-существительное, описание, условия, сумма, где,
для кого, польза, срок) и предлагает уточняющие вопросы.

Основной провайдер — YandexGPT (российский, без VPN). Если ключа нет или он
не ответил — мягкий офлайн-фолбэк (слабый, но не падает).
"""

from __future__ import annotations

import json
import re

from .config import settings

# Схема категорий и допустимых значений полей (та же, что на клиенте).
CARD_CATS = {
    "time_skill": {
        "label": "Время / Навык / Услуга",
        "fields": {
            "level": ["Новичок", "Уверенный любитель", "Профи"],
            "volume": "строка (сколько времени/регулярность)",
            "when": ["Будни", "Выходные", "Гибко"],
            "where": ["У меня", "У тебя", "Онлайн"],
        },
    },
    "thing": {
        "label": "Вещь / Товар",
        "fields": {
            "condition": ["Новое", "Б/у как новое", "Отличное", "Хорошее", "С дефектами", "На ремонт"],
            "where": "строка (город/район)",
        },
    },
    "space": {
        "label": "Пространство / Место",
        "fields": {
            "purpose": ["Хранение", "Работа/учёба", "Мероприятие", "Проживание"],
            "capacity": "строка (площадь/вместимость)",
            "schedule": ["Разово", "Регулярно", "Длительно", "Навсегда"],
        },
    },
    "knowledge": {
        "label": "Знание / Опыт",
        "fields": {
            "topic": "строка (тема)",
            "format": ["Краткий ответ", "Консультация до 60 мин", "Менторство", "Записанные уроки"],
            "channel": ["Текст", "Видео", "Встреча", "Телефон"],
        },
    },
}
TERMS = ["Дар", "За баллы", "Обмен", "Аренда", "Деньги"]


def _schema_text() -> str:
    lines = []
    for key, cat in CARD_CATS.items():
        parts = [f"{fk}: {fv if isinstance(fv, str) else '/'.join(fv)}" for fk, fv in cat["fields"].items()]
        lines.append(f"- {key} ({cat['label']}): " + "; ".join(parts))
    return "\n".join(lines)


def _empty_draft() -> dict:
    return {"category": "", "title": "", "description": "", "fields": {}, "amount": "",
            "ideal": "", "impact": "", "questions": []}


def extract_card(text: str, kind: str) -> dict:
    if settings.yandex_api_key and settings.yandex_folder_id:
        try:
            return _yandex_extract(text, kind)
        except Exception:
            pass
    return _offline_extract(text, kind)


def _yandex_extract(text: str, kind: str) -> dict:
    import httpx

    side = "ресурс (что человек даёт)" if kind == "give" else "потребность/проект (что человеку нужно)"
    system = (
        "Ты помощник сервиса обмена ресурсами. По свободному рассказу человека собери "
        f"карточку: это {side}. Категории и поля:\n{_schema_text()}\n"
        f"Условия (terms) — массив из: {', '.join(TERMS)}.\n"
        "Верни СТРОГО JSON с ключами: category (один из ключей выше), "
        "title (КОРОТКОЕ название существительным, без глагола, напр. «Жильё у моря»), "
        "description (подробное описание своими словами), fields (объект с полями категории; "
        "terms — массив; where/city — строкой), amount (сколько денег/баллов, если применимо, иначе пусто), "
        "ideal (кому идеально подойдёт — для ресурса), impact (какая польза миру/людям — для потребности), "
        "questions (массив 1-3 коротких уточняющих вопросов по важному, чего не хватает). "
        "Не выдумывай факты; если поля нет в рассказе — оставь пустым."
    )
    resp = httpx.post(
        "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
        headers={"Authorization": f"Api-Key {settings.yandex_api_key}", "x-folder-id": settings.yandex_folder_id},
        json={
            "modelUri": f"gpt://{settings.yandex_folder_id}/{settings.yandex_model}/latest",
            "completionOptions": {"stream": False, "temperature": 0.2, "maxTokens": 2000},
            "messages": [{"role": "system", "text": system}, {"role": "user", "text": text}],
        },
        timeout=45,
    )
    resp.raise_for_status()
    raw = resp.json()["result"]["alternatives"][0]["message"]["text"]
    data = json.loads(re.search(r"\{.*\}", raw, re.DOTALL).group(0))
    draft = _empty_draft()
    for k in ("category", "title", "description", "amount", "ideal", "impact"):
        if data.get(k):
            draft[k] = data[k]
    if isinstance(data.get("fields"), dict):
        draft["fields"] = data["fields"]
    if isinstance(data.get("questions"), list):
        draft["questions"] = [str(q) for q in data["questions"]][:3]
    draft["provider"] = "yandex"
    return draft


_CAT_HINTS = {
    "space": ["жиль", "квартир", "помещ", "место", "комнат", "офис", "площад", "аренд"],
    "knowledge": ["знан", "опыт", "курс", "ментор", "консульт", "научу", "объясн", "тема"],
    "thing": ["вещь", "товар", "отдам", "продам", "куплю", "предмет", "инструмент"],
    "time_skill": ["масс", "помощь", "услуг", "умею", "сделаю", "время", "навык"],
}


def _offline_extract(text: str, kind: str) -> dict:
    draft = _empty_draft()
    low = (text or "").lower()
    draft["category"] = next((c for c, hints in _CAT_HINTS.items() if any(h in low for h in hints)), "time_skill")
    words = (text or "").strip().split()
    draft["title"] = " ".join(words[:5])
    draft["description"] = (text or "").strip()
    terms = []
    if re.search(r"балл", low):
        terms.append("За баллы")
    if re.search(r"деньг|руб|₽|продам|куплю|плат", low):
        terms.append("Деньги")
    if re.search(r"обмен|бартер", low):
        terms.append("Обмен")
    if re.search(r"\bдар\b|бесплатн", low):
        terms.append("Дар")
    if terms:
        draft["fields"]["terms"] = terms
    draft["questions"] = ["Уточните условия (дар / обмен / за баллы / деньги)?",
                          "Где это происходит?"]
    draft["provider"] = "local"
    return draft
