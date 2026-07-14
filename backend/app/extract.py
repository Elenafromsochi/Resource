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
        "critical": ["level", "volume", "where"],
    },
    "thing": {
        "label": "Вещь / Товар",
        "fields": {
            "condition": ["Новое", "Б/у как новое", "Отличное", "Хорошее", "С дефектами", "На ремонт"],
            "where": "строка (город/район)",
        },
        "critical": ["condition", "where"],
    },
    "space": {
        "label": "Пространство / Место",
        "fields": {
            "purpose": ["Хранение", "Работа/учёба", "Мероприятие", "Проживание"],
            "capacity": "строка (площадь/вместимость)",
            "schedule": ["Разово", "Регулярно", "Длительно", "Навсегда"],
        },
        "critical": ["capacity", "schedule"],
    },
    "knowledge": {
        "label": "Знание / Опыт",
        "fields": {
            "topic": "строка (тема)",
            "format": ["Краткий ответ", "Консультация до 60 мин", "Менторство", "Записанные уроки"],
            "channel": ["Текст", "Видео", "Встреча", "Телефон"],
        },
        "critical": ["topic", "format"],
    },
}
TERMS = ["Дар", "За баллы", "Обмен", "Аренда", "Деньги"]

# Вопросы-подсказки для критичных полей
_FIELD_QUESTIONS = {
    "level": "Какой уровень expertise? (Новичок / Любитель / Профи)",
    "volume": "Сколько времени/регулярность? (разово / регулярно / длительно)",
    "where": "Где это происходит? (У меня / У тебя / Онлайн)",
    "condition": "Какое состояние? (Новое / Б/у как новое / Отличное / Хорошее / С дефектами)",
    "capacity": "Размер/площадь/вместимость? (точные цифры)",
    "schedule": "График использования? (Разово / Регулярно / Длительно / Навсегда)",
    "topic": "Сфера/тема знания?",
    "format": "Формат? (Ответ / Консультация / Менторство / Уроки)",
    "purpose": "Назначение? (Хранение / Работа / Мероприятие / Проживание)",
}


def _schema_text() -> str:
    lines = []
    for key, cat in CARD_CATS.items():
        parts = [f"{fk}: {fv if isinstance(fv, str) else '/'.join(fv)}" for fk, fv in cat["fields"].items()]
        lines.append(f"- {key} ({cat['label']}): " + "; ".join(parts))
    return "\n".join(lines)


def _empty_draft() -> dict:
    return {"category": "", "title": "", "description": "", "fields": {},
            "amount_money": "", "amount_points": "", "ideal": "", "impact": "", "questions": []}


def _analyze_missing_fields(draft: dict) -> list[str]:
    """Выявить пустые критичные поля и сгенерировать вопросы."""
    if not draft.get("category") or draft["category"] not in CARD_CATS:
        return []

    cat_info = CARD_CATS[draft["category"]]
    critical = cat_info.get("critical", [])
    questions = []

    for field in critical:
        val = draft.get("fields", {}).get(field, "")
        # Проверяем, пусто ли поле (или пустой список)
        if not val or (isinstance(val, list) and len(val) == 0):
            q = _FIELD_QUESTIONS.get(field, f"Уточните {field}?")
            questions.append(q)

    return questions[:3]  # Макс 3 вопроса


def apply_clarifications(draft: dict, clarifications: dict) -> dict:
    """Применить ответы пользователя на уточняющие вопросы к карточке.

    Args:
        draft: исходная карточка с пустыми полями
        clarifications: {'level': 'Профи', 'where': 'У меня', ...}

    Returns:
        обновленная карточка
    """
    if not clarifications:
        return draft

    updated = {**draft}
    if "fields" not in updated:
        updated["fields"] = {}

    # Перебираем ответы и добавляем их в правильные поля
    for key, value in clarifications.items():
        if key in _FIELD_QUESTIONS and value:  # Проверяем, что это известное поле
            updated["fields"][key] = value

    # Пересчитываем вопросы - может быть, теперь все критичные поля заполнены
    updated["questions"] = _analyze_missing_fields(updated)

    return updated


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
        "terms — массив; where/city — строкой), amount_money (сколько денег, если в terms есть «Деньги», иначе пусто), amount_points (сколько баллов, если в terms есть «За баллы», иначе пусто), "
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
    for k in ("category", "title", "description", "amount_money", "amount_points", "ideal", "impact"):
        if data.get(k):
            draft[k] = data[k]
    if isinstance(data.get("fields"), dict):
        draft["fields"] = data["fields"]
    # Если ИИ вернул вопросы — используем их; если нет — анализируем критичные поля
    if isinstance(data.get("questions"), list) and data["questions"]:
        draft["questions"] = [str(q) for q in data["questions"]][:3]
    else:
        draft["questions"] = _analyze_missing_fields(draft)
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
    # Анализируем критичные поля и генерируем вопросы
    draft["questions"] = _analyze_missing_fields(draft)
    draft["provider"] = "local"
    return draft
