"""ИИ-ассистент формы «Даю/Прошу».

По брифу: ИИ задаёт до 5 уточняющих вопросов в одном сообщении, предлагает
короткие варианты ответов, принимает голос. У ресурсодателя дополнительно
спрашивает: кому/в каких условиях ресурс идеально подойдёт.

Здесь — детерминированная заглушка-генератор: она смотрит, какие поля категории
ещё не заполнены, и формирует вопросы с короткими вариантами. Это пригодно для
прототипа и офлайн-тестов. В проде сюда подключается LLM (Claude/DeepSeek) —
интерфейс `clarifying_questions(...)` остаётся тем же.
"""

from __future__ import annotations

from .categories import TRANSFER_TERMS, fields_for
from .matching import ORDINAL_SCALES

MAX_QUESTIONS = 5

# Короткие варианты ответов под отдельные поля.
_SUGGESTED_OPTIONS: dict[str, list[str]] = {
    "transfer_terms": TRANSFER_TERMS,
    "qualification": ORDINAL_SCALES["qualification"],
    "condition": ORDINAL_SCALES["condition"],
    "format": ["встреча", "онлайн", "текст", "видео"],
    "channel": ["telegram", "звонок", "встреча"],
    "availability": ["будни", "выходные", "вечера", "гибко"],
    "schedule": ["будни", "выходные", "круглосуточно", "по записи"],
}


def clarifying_questions(category: str, filled_fields: dict, side: str) -> list[dict]:
    """Вернуть до 5 уточняющих вопросов по незаполненным полям категории.

    side: "give" (ресурс) или "ask" (потребность).
    Каждый вопрос: {field, question, options (короткие варианты), accepts_voice}.
    """
    questions: list[dict] = []
    for spec in fields_for(category):
        if len(questions) >= MAX_QUESTIONS:
            break
        key = spec["key"]
        value = filled_fields.get(key)
        if value not in (None, "", [], {}):
            continue
        questions.append(
            {
                "field": key,
                "question": f"Уточните: {spec['label'].lower()}?",
                "options": _SUGGESTED_OPTIONS.get(key, []),
                "accepts_voice": True,
            }
        )

    # Доп. вопрос ресурсодателю — «кому идеально подойдёт».
    if side == "give" and len(questions) < MAX_QUESTIONS:
        questions.append(
            {
                "field": "ideal_for",
                "question": "Кому и в каких условиях этот ресурс подойдёт идеально?",
                "options": [],
                "accepts_voice": True,
            }
        )
    return questions[:MAX_QUESTIONS]
