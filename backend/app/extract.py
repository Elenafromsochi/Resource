"""
Intake система для Resource: два независимых вызова модели.

1. ПРОМПТ 1 (extract_intake) — только извлечение, без додумывания
2. ПРОМПТ 2 (clarify_intake) — умные вопросы на основе пустых полей
3. formulas.py — расчёт совпадений (КОД, не модель)
"""

from __future__ import annotations

import json
import httpx
from typing import Optional

from .config import settings

# Новая структура карточки
INTAKE_SCHEMA = {
    "mode": {"type": "string", "enum": ["resource", "need", None]},
    "category": {"type": "string", "enum": ["skill", "thing", "space", "knowledge", None]},
    "object_text": {"type": "string or null", "example": "Массаж спины после травм"},
    "object_level": {"type": "int or null", "description": "зависит от категории"},
    "transfer_form": {"type": "string", "enum": ["permanent", "temporary", None]},
    "when_type": {"type": "string", "enum": ["once", "period", "regular", None]},
    "when_window": {"type": "string or null", "example": "по выходным, 3 раза в неделю"},
    "urgency": {"type": "string", "enum": ["urgent", "week", "relaxed", None]},
    "where_mode": {"type": "string", "enum": ["online", "offline", None]},
    "where_geo": {"type": "string or null", "example": "м.Студенческая, Москва"},
    "where_side": {"type": "string", "enum": ["mine", "yours", "neutral", None]},
    "counter_value": {"type": "list or null", "enum": ["gift", "unit", "barter", "money"]},
    "priority_fields": {"type": "list or null"},
    "evidence": {"type": "dict", "description": "дословные фрагменты из сообщения"},
}

# Значения object_level по категориям
OBJECT_LEVELS = {
    "skill": {
        1: "любитель",
        2: "уверенный любитель",
        3: "профессионал"
    },
    "thing": {
        1: "требует ремонта",
        2: "с дефектами",
        3: "б/у хорошее",
        4: "б/у отличное",
        5: "как новое",
        6: "новое"
    },
    "space": {
        1: "1-5 м²",
        2: "5-20 м²",
        3: "20-50 м²",
        4: "50+ м²"
    },
    "knowledge": {
        1: "короткий ответ",
        2: "консультация",
        3: "менторство",
        4: "курс"
    }
}

# Порядок приоритета вопросов
QUESTION_PRIORITY = [
    "category",
    "object_level",
    "transfer_form",
    "when_type",
    "when_window",
    "urgency",
    "where_mode",
    "where_geo",
    "where_side",
    "counter_value",
    "priority_fields",
]


def _empty_intake() -> dict:
    """Пустая карточка intake."""
    return {
        "mode": None,
        "category": None,
        "object_text": None,
        "object_level": None,
        "transfer_form": None,
        "when_type": None,
        "when_window": None,
        "urgency": None,
        "where_mode": None,
        "where_geo": None,
        "where_side": None,
        "counter_value": None,
        "priority_fields": None,
        "evidence": {},
    }


def extract_intake(text: str, current_state: dict | None = None) -> dict:
    """
    ПРОМПТ 1: Извлечение данных из текста пользователя.

    ГЛАВНОЕ: НЕ додумываем. Только то, что ЯВНО сказано.
    Для каждого заполненного поля — evidence (дословный фрагмент).

    Args:
        text: сообщение пользователя
        current_state: текущее состояние карточки (для updates)

    Returns:
        JSON с новой структурой intake
    """
    if not text or not text.strip():
        return _empty_intake()

    # Вызываем модель (YandexGPT или offline fallback)
    if settings.yandex_api_key and settings.yandex_folder_id:
        try:
            return _extract_yandex(text, current_state)
        except Exception:
            pass

    return _extract_offline(text, current_state)


def _extract_yandex(text: str, current_state: dict | None) -> dict:
    """Извлечение через YandexGPT."""

    system_prompt = """Ты — модуль извлечения данных сервиса «Ресурс». Твоя единственная задача — разложить сказанное пользователем по полям структуры. Ты НЕ общаешься с пользователем и НЕ задаёшь вопросов.

ГЛАВНОЕ ПРАВИЛО — НЕ ДОДУМЫВАЙ.
- Поле заполняется только если пользователь сказал это прямо или это следует однозначно.
- Если пользователь не назвал район — where_geo остаётся null.
- Если пользователь не назвал уровень — object_level остаётся null.
- Для каждого заполненного поля ты ОБЯЗАН привести evidence — дословный фрагмент сообщения.
- Нет фрагмента — значит null.
- Ранее заполненные поля не перезаписывай, если пользователь их прямо не исправил.

ОПРЕДЕЛЕНИЕ mode:
- resource — человек говорит, что может дать, умеет, у него есть, готов поделиться.
- need — человек говорит, что ему нужно, ищет, не хватает, хочет найти.
- Если в одном сообщении и то и другое — заполни mode тем, что названо первым.

ОПРЕДЕЛЕНИЕ transfer_form (только для thing и space):
- permanent — навсегда, продать, переехать
- temporary — в аренду, на время, одолжить
- Для skill и knowledge — всегда null.

object_text — своими словами пользователя, максимально конкретно, с сохранением нюансов.

ЗНАЧЕНИЯ object_level:
- skill: 1 любитель, 2 уверенный любитель, 3 профессионал
- thing: 1 требует ремонта, 2 с дефектами, 3 б/у хорошее, 4 б/у отличное, 5 как новое, 6 новое
- space: 1-6 по размеру (1 = 1-5м², 6 = 50+м²)
- knowledge: 1 ответ, 2 консультация, 3 менторство, 4 курс

Возвращай ТОЛЬКО JSON, без пояснений, без markdown."""

    resp = httpx.post(
        "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
        headers={
            "Authorization": f"Api-Key {settings.yandex_api_key}",
            "x-folder-id": settings.yandex_folder_id
        },
        json={
            "modelUri": f"gpt://{settings.yandex_folder_id}/yandexgpt/latest",
            "completionOptions": {"stream": False, "temperature": 0.1, "maxTokens": 1000},
            "messages": [
                {"role": "system", "text": system_prompt},
                {"role": "user", "text": text},
            ],
        },
        timeout=30,
    )
    resp.raise_for_status()

    raw = resp.json()["result"]["alternatives"][0]["message"]["text"]
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Если не удалось распарсить — офлайн fallback
        return _extract_offline(text, current_state)

    # Мёджим current_state и новые данные
    result = current_state.copy() if current_state else _empty_intake()

    # Обновляем только новые/изменённые поля
    for key in result.keys():
        if key in data and data[key] is not None:
            result[key] = data[key]

    return result


def _extract_offline(text: str, current_state: dict | None) -> dict:
    """Офлайн фолбэк (простой парсинг)."""
    result = current_state.copy() if current_state else _empty_intake()

    low = text.lower()

    # Простое определение mode
    if any(w in low for w in ["ищу", "нужно", "хочу найти", "нужна", "не хватает"]):
        result["mode"] = "need"
    elif any(w in low for w in ["даю", "умею", "провожу", "есть у меня", "готов", "могу помочь"]):
        result["mode"] = "resource"

    # object_text — первые 5 слов
    words = text.strip().split()
    if len(words) >= 3:
        result["object_text"] = " ".join(words[:8])

    # Простой поиск локации
    if "онлайн" in low or "online" in low:
        result["where_mode"] = "online"
    elif "у меня" in low:
        result["where_side"] = "mine"
        result["where_mode"] = "offline"
    elif "у тебя" in low:
        result["where_side"] = "yours"
        result["where_mode"] = "offline"

    # Срочность
    if "срочно" in low or "urgent" in low:
        result["urgency"] = "urgent"

    # Условия
    counter = []
    if "деньг" in low or "руб" in low or "платить" in low:
        counter.append("money")
    if "дар" in low or "бесплатн" in low:
        counter.append("gift")
    if "обмен" in low:
        counter.append("barter")
    if "балл" in low:
        counter.append("unit")
    if counter:
        result["counter_value"] = counter

    # evidence (хотя бы для основных полей)
    if result["object_text"]:
        result["evidence"]["object_text"] = result["object_text"]

    return result


def clarify_intake(state: dict) -> dict:
    """
    ПРОМПТ 2: Генерирует вопросы на основе пустых полей.

    Args:
        state: текущее состояние карточки (результат extract_intake)

    Returns:
        {
            "questions": [
                {
                    "field": "where_geo",
                    "text": "В каком районе ты работаешь?",
                    "explanation": "чтобы показать тебя нужным людям",
                    "variants": ["м.Студенческая", "м.Красные Ворота", "онлайн", "свой вариант"]
                },
                ...
            ],
            "stop_reason": "ready_to_search" | "need_more_info" | null
        }
    """

    questions = []

    # Ищем пустые критичные поля по приоритету
    for field in QUESTION_PRIORITY:
        if len(questions) >= 3:
            break

        current_value = state.get(field)

        # Пропускаем если уже заполнено
        if current_value is not None and current_value != "":
            continue

        # Генерируем вопрос
        question = _generate_question(field, state)
        if question:
            questions.append(question)

    # Проверяем стоп-критерий
    stop_reason = _check_stop_criteria(state)

    return {
        "questions": questions,
        "stop_reason": stop_reason,
    }


def _generate_question(field: str, state: dict) -> dict | None:
    """Генерирует вопрос для пустого поля."""

    mode = state.get("mode")
    category = state.get("category")

    # CATEGORY (обязателен)
    if field == "category" and state.get("category") is None:
        return {
            "field": "category",
            "text": "К какой категории это ближе?",
            "explanation": "от этого зависит, какие варианты мы найдём",
            "variants": ["Время/Навык/Услуга", "Вещь/Товар", "Пространство/Место", "Знание/Опыт"],
        }

    # Если category не выбран — остальные вопросы не имеют смысла
    if category is None:
        return None

    # OBJECT_LEVEL (специфичный для категории)
    if field == "object_level" and state.get("object_level") is None:
        if category == "skill":
            text = "Какой уровень опыта?" if mode == "resource" else "Какой уровень нужен?"
            variants = ["1-2 года (любитель)", "3-5 лет", "6+ лет (профи)"]
        elif category == "thing":
            text = "Какое состояние?" if mode == "resource" else "Какое минимальное состояние?"
            variants = ["Новое", "Б/у отличное", "Б/у хорошее", "С дефектами"]
        elif category == "space":
            text = "Примерно сколько кв.м. или вместимость?"
            variants = ["5-20 м²", "20-50 м²", "50-100 м²", "100+ м²"]
        elif category == "knowledge":
            text = "Какой формат?" if mode == "resource" else "Какой формат нужен?"
            variants = ["Краткий ответ", "Консультация", "Менторство", "Полный курс"]
        else:
            return None

        return {
            "field": "object_level",
            "text": text,
            "explanation": "это важно для хорошего матча",
            "variants": variants,
        }

    # WHEN_TYPE (для большинства категорий)
    if field == "when_type" and state.get("when_type") is None:
        if category in ["skill", "knowledge"]:
            text = "Как часто?" if mode == "resource" else "Как часто нужно?"
            variants = ["Разово, один раз", "Несколько раз периодически", "Регулярно"]
            explanation = "расписание важно для координации"
        else:
            return None

        return {
            "field": "when_type",
            "text": text,
            "explanation": explanation,
            "variants": variants,
        }

    # WHERE_GEO (для offline сценариев)
    if field == "where_geo" and state.get("where_geo") is None and state.get("where_mode") == "offline":
        text = "В каком районе или городе?" if mode == "resource" else "Где нужно?"
        explanation = "чтоб показать людей рядом или предложить альтернативу"

        return {
            "field": "where_geo",
            "text": text,
            "explanation": explanation,
            "variants": ["Москва, центр", "Москва, окраины", "МО (подмосковье)", "свой вариант"],
        }

    # COUNTER_VALUE (условия оплаты/обмена)
    if field == "counter_value" and state.get("counter_value") is None:
        if mode == "resource":
            text = "На какие условия?"
            variants = ["Дар (бесплатно)", "Деньги", "Обмен", "За баллы"]
        else:
            text = "Какие условия тебе подходят?"
            variants = ["Дар (ищу добрых людей)", "Готов платить", "Обмен", "За баллы"]
        explanation = "это влияет на поиск совпадений"

        return {
            "field": "counter_value",
            "text": text,
            "explanation": explanation,
            "variants": variants,
        }

    return None


def _check_stop_criteria(state: dict) -> str | None:
    """
    Проверяет стоп-критерий: достаточно ли данных для поиска?

    Returns:
        "ready_to_search" если хватает
        "need_more_info" если не хватает
        None если можем продолжить спрашивать
    """

    # Обязательные поля
    has_category = state.get("category") is not None
    has_object_text = state.get("object_text") is not None
    has_level = state.get("object_level") is not None

    # Хотя бы одно из when/where
    has_when_or_where = (
        state.get("when_type") is not None or
        state.get("where_mode") is not None or
        state.get("where_geo") is not None
    )

    if has_category and has_object_text and has_level and has_when_or_where:
        return "ready_to_search"

    return None

# --- Старая система (для обратной совместимости) ---
# Схема категорий и допустимых значений полей (та же, что на клиенте).
CARD_CATS = {
    "time_skill": {
        "label": "Время / Навык / Услуга",
        "fields": {
            "level": "строка (лет опыта, напр.: 5 лет)",
            "volume": "строка (сколько времени/регулярность)",
            "when": ["Будни", "Выходные", "Гибко"],
            "where": "строка (город/район или онлайн)",
        },
        "critical": ["level", "where"],
    },
    "thing": {
        "label": "Вещь / Товар",
        "fields": {
            "condition": ["Новое", "Б/у как новое", "Отличное", "Хорошее", "С дефектами", "На ремонт"],
            "where": "строка (город/район/адрес)",
            "size": "строка (размер/габариты если важно)",
        },
        "critical": ["condition", "where"],
    },
    "space": {
        "label": "Пространство / Место",
        "fields": {
            "purpose": ["Хранение", "Работа/учёба", "Мероприятие", "Проживание"],
            "capacity": "строка (кв.м., или вместимость людей)",
            "location": "строка (район/адрес/ближайшее метро)",
            "schedule": ["Разово", "Регулярно", "Длительно", "Навсегда"],
        },
        "critical": ["capacity", "schedule"],
    },
    "knowledge": {
        "label": "Знание / Опыт",
        "fields": {
            "topic": "строка (узко и конкретно, не просто 'дизайн')",
            "target_level": "строка (для какого уровня: начинающие/средний/продвинутые)",
            "format": ["Краткий ответ", "Консультация до 60 мин", "Менторство", "Записанные уроки"],
            "channel": ["Текст", "Видео", "Встреча", "Телефон"],
        },
        "critical": ["topic", "format"],
    },
}
TERMS = ["Дар", "За баллы", "Обмен", "Аренда", "Деньги"]

_FIELD_QUESTIONS = {
    "level": "Сколько лет вы этим занимаетесь? (реальный опыт)",
    "volume": "Сколько часов в неделю/месяц можете уделять?",
    "where": "Точный адрес или район? (для встречи / хранения / работы)",
    "condition": "Описание дефектов? (если есть — важно для matching)",
    "size": "Точные размеры или вес? (для доставки и подгона)",
    "capacity": "Точно кв.м. или вместимость людей?",
    "location": "Район? Есть доступ парковка/лифт? (важные детали)",
    "schedule": "Гибкие даты или жёсткие сроки?",
    "topic": "Совсем узко: не 'дизайн', а 'веб для e-commerce' или 'UI для мобильных'?",
    "target_level": "Для какого уровня учеников? (совсем с нуля / уже что-то знают / продвинутые)",
    "format": "Почему именно этот формат? (что вам нужнее всего?)",
    "purpose": "Для чего конкретно? (какая задача?)",
}


def _schema_text() -> str:
    lines = []
    for key, cat in CARD_CATS.items():
        parts = [f"{fk}: {fv if isinstance(fv, str) else '/'.join(fv)}" for fk, fv in cat["fields"].items()]
        lines.append(f"- {key} ({cat['label']}): " + "; ".join(parts))
    return "\n".join(lines)


def _normalize_title(title: str) -> str:
    if not title:
        return ""
    title = title.strip()
    if len(title) > 1:
        title = title[0].upper() + title[1:].lower()
    title = title.rstrip('.')
    return title


def _empty_draft() -> dict:
    return {"category": "", "title": "", "description": "", "fields": {},
            "amount_money": "", "amount_points": "", "ideal": "", "impact": "", "questions": [], "questions_map": {}}


def _analyze_missing_fields(draft: dict) -> tuple[list[str], dict]:
    if not draft.get("category") or draft["category"] not in CARD_CATS:
        return [], {}
    cat_info = CARD_CATS[draft["category"]]
    critical = cat_info.get("critical", [])
    questions = []
    questions_map = {}
    for field in critical:
        val = draft.get("fields", {}).get(field, "")
        if not val or (isinstance(val, list) and len(val) == 0):
            q = _FIELD_QUESTIONS.get(field, f"Уточните {field}?")
            questions.append(q)
            questions_map[field] = q
    return questions[:3], {k: questions_map[k] for k in list(questions_map.keys())[:3]}


def apply_clarifications(draft: dict, clarifications: dict) -> dict:
    if not clarifications:
        return draft
    updated = {**draft}
    if "fields" not in updated:
        updated["fields"] = {}
    for key, value in clarifications.items():
        if key in _FIELD_QUESTIONS and value:
            updated["fields"][key] = value
    questions, questions_map = _analyze_missing_fields(updated)
    updated["questions"] = questions
    updated["questions_map"] = questions_map
    return updated


def extract_card(text: str, kind: str) -> dict:
    if settings.yandex_api_key and settings.yandex_folder_id:
        try:
            return _yandex_extract_card(text, kind)
        except Exception:
            pass
    return _offline_extract_card(text, kind)


def _yandex_extract_card(text: str, kind: str) -> dict:
    import re
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
    for k in ("category", "description", "amount_money", "amount_points", "ideal", "impact"):
        if data.get(k):
            draft[k] = data[k]
    if data.get("title"):
        draft["title"] = _normalize_title(data["title"])
    if isinstance(data.get("fields"), dict):
        draft["fields"] = data["fields"]
    if isinstance(data.get("questions"), list) and data["questions"]:
        draft["questions"] = [str(q) for q in data["questions"]][:3]
        draft["questions_map"] = {}
    else:
        questions, questions_map = _analyze_missing_fields(draft)
        draft["questions"] = questions
        draft["questions_map"] = questions_map
    draft["provider"] = "yandex"
    return draft


_CAT_HINTS = {
    "space": ["жиль", "квартир", "помещ", "место", "комнат", "офис", "площад", "аренд"],
    "knowledge": ["знан", "опыт", "курс", "ментор", "консульт", "научу", "объясн", "тема"],
    "thing": ["вещь", "товар", "отдам", "продам", "куплю", "предмет", "инструмент"],
    "time_skill": ["масс", "помощь", "услуг", "умею", "сделаю", "время", "навык"],
}


def _offline_extract_card(text: str, kind: str) -> dict:
    import re
    draft = _empty_draft()
    low = (text or "").lower()
    draft["category"] = next((c for c, hints in _CAT_HINTS.items() if any(h in low for h in hints)), "time_skill")
    words = (text or "").strip().split()
    draft["title"] = _normalize_title(" ".join(words[:5]))
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
    questions, questions_map = _analyze_missing_fields(draft)
    draft["questions"] = questions
    draft["questions_map"] = questions_map
    draft["provider"] = "local"
    return draft
