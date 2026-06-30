"""Категории ресурсов/потребностей и их параметры.

Четыре категории из брифа. У каждой — свой набор полей. Часть полей помечена
как "важные" (вес x4 при мэтчинге), остальные имеют вес x1.

Структура одинаковая и для "Даю" (resource), и для "Прошу" (need) — это и есть
зеркальность: мэтчинг сравнивает одни и те же параметры с двух сторон.
"""

from __future__ import annotations

# Веса параметров при расчёте балла соответствия.
WEIGHT_IMPORTANT = 4
WEIGHT_NORMAL = 1

# Способы передачи ценности (общий справочник для всех категорий).
TRANSFER_TERMS = ["gift", "rent", "barter", "money", "internal_unit"]

# Описание категорий. Поля:
#   key      — машинный ключ поля (хранится в JSON ресурса/потребности);
#   label    — человекочитаемая подпись;
#   weight   — вес при мэтчинге;
#   match    — как сравнивать ("equals", "overlap", "gte", "location", "terms").
CATEGORIES: dict[str, dict] = {
    "time_skill": {
        "label": "Время / Навык / Услуга",
        "fields": [
            {"key": "qualification", "label": "Уровень квалификации", "weight": WEIGHT_IMPORTANT, "match": "gte"},
            {"key": "volume", "label": "Объём / длительность", "weight": WEIGHT_NORMAL, "match": "gte"},
            {"key": "availability", "label": "Доступность", "weight": WEIGHT_IMPORTANT, "match": "overlap"},
            {"key": "transfer_terms", "label": "Условия передачи", "weight": WEIGHT_IMPORTANT, "match": "terms"},
            {"key": "location", "label": "Место", "weight": WEIGHT_NORMAL, "match": "location"},
        ],
    },
    "thing": {
        "label": "Вещь / Товар",
        "fields": [
            {"key": "condition", "label": "Состояние", "weight": WEIGHT_NORMAL, "match": "gte"},
            {"key": "transfer_terms", "label": "Условия передачи", "weight": WEIGHT_IMPORTANT, "match": "terms"},
            {"key": "location", "label": "Локация", "weight": WEIGHT_IMPORTANT, "match": "location"},
        ],
    },
    "space": {
        "label": "Пространство / Место",
        "fields": [
            {"key": "purpose", "label": "Цель использования", "weight": WEIGHT_IMPORTANT, "match": "equals"},
            {"key": "capacity", "label": "Площадь / вместимость", "weight": WEIGHT_NORMAL, "match": "gte"},
            {"key": "schedule", "label": "График", "weight": WEIGHT_IMPORTANT, "match": "overlap"},
            {"key": "transfer_terms", "label": "Условия", "weight": WEIGHT_NORMAL, "match": "terms"},
            {"key": "location", "label": "Локация", "weight": WEIGHT_IMPORTANT, "match": "location"},
        ],
    },
    "knowledge": {
        "label": "Знание / Опыт",
        "fields": [
            {"key": "topic", "label": "Тема", "weight": WEIGHT_IMPORTANT, "match": "equals"},
            {"key": "format", "label": "Формат передачи", "weight": WEIGHT_NORMAL, "match": "overlap"},
            {"key": "channel", "label": "Способ общения", "weight": WEIGHT_NORMAL, "match": "overlap"},
            {"key": "transfer_terms", "label": "Условия", "weight": WEIGHT_NORMAL, "match": "terms"},
        ],
    },
}

# Порядковая шкала для квалификации/состояния (для сравнения "не хуже, чем просят").
ORDINAL_SCALES: dict[str, list[str]] = {
    "qualification": ["novice", "intermediate", "advanced", "expert"],
    "condition": ["poor", "used", "good", "new"],
}


def category_keys() -> list[str]:
    return list(CATEGORIES.keys())


def fields_for(category: str) -> list[dict]:
    cat = CATEGORIES.get(category)
    if cat is None:
        raise KeyError(f"Неизвестная категория: {category}")
    return cat["fields"]
