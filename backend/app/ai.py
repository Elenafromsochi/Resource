"""ИИ-помощник заполнения личного кабинета.

Пользователь рассказывает о себе свободным текстом — помощник раскладывает рассказ
по полям профиля (черновик) и задаёт уточняющие вопросы по тому, чего не хватает.

Два провайдера за одним интерфейсом `assist(text, current)`:
  • ClaudeAssistant — реальный LLM (если задан ANTHROPIC_API_KEY и установлен SDK);
  • LocalAssistant  — офлайн-эвристика, работает без ключей (для прототипа/тестов).

При любой ошибке реального провайдера — мягкий откат на офлайн-помощника.
"""

from __future__ import annotations

import json
import re

from .config import settings

# Поля профиля: ключ, подпись, тип, примеры для вопросов.
PROFILE_FIELDS = [
    {"key": "full_name", "label": "Имя", "type": "str", "examples": ["Анна Иванова"]},
    {"key": "occupation", "label": "Род занятий", "type": "str", "examples": ["дизайнер", "репетитор", "столяр"]},
    {"key": "city", "label": "Город", "type": "str", "examples": ["Москва", "Сочи", "удалённо"]},
    {"key": "skills", "label": "Навыки", "type": "list", "examples": ["вёрстка", "фотография", "ремонт"]},
    {"key": "interests", "label": "Интересы", "type": "list", "examples": ["спорт", "музыка", "путешествия"]},
    {"key": "goals", "label": "Что вы ищете", "type": "str", "examples": ["новые проекты", "обмен опытом"]},
    {"key": "about", "label": "О себе", "type": "str", "examples": []},
    {"key": "contacts", "label": "Контакты", "type": "str", "examples": ["@nick", "почта"]},
]
_FIELD_BY_KEY = {f["key"]: f for f in PROFILE_FIELDS}
LIST_FIELDS = {f["key"] for f in PROFILE_FIELDS if f["type"] == "list"}


def _split_list(segment: str) -> list[str]:
    parts = re.split(r"[,;]| и |\n", segment)
    items = [p.strip(" .—-") for p in parts if p.strip(" .—-")]
    # без дублей, сохраняя порядок
    seen, out = set(), []
    for it in items:
        low = it.lower()
        if low not in seen:
            seen.add(low)
            out.append(it)
    return out[:10]


def _grab(text: str, keywords: list[str]) -> str:
    """Вернуть фрагмент текста после одного из ключевых слов до конца предложения."""
    for kw in keywords:
        m = re.search(rf"{kw}\s*[:\-—]?\s*([^.\n!?]+)", text, re.IGNORECASE)
        if m and m.group(1).strip():
            return m.group(1).strip()
    return ""


class LocalAssistant:
    provider = "local"

    def assist(self, text: str, current: dict) -> dict:
        draft = dict(current)
        text = (text or "").strip()

        name = _grab(text, ["меня зовут", "зовут меня", "моё имя", "мое имя", "имя"])
        if name:
            draft["full_name"] = name.split(",")[0].strip()[:80]

        city = _grab(text, ["живу в городе", "живу в", "из города", "город"])
        if city:
            draft["city"] = city.split(",")[0].strip()[:60]

        occupation = _grab(text, ["по профессии", "работаю", "я —", "профессия"])
        if occupation:
            draft["occupation"] = occupation.split(",")[0].strip()[:80]

        skills = _grab(text, ["навыки", "умею", "владею", "могу"])
        if skills:
            draft["skills"] = _split_list(skills)

        interests = _grab(text, ["увлекаюсь", "интересы", "хобби", "люблю"])
        if interests:
            draft["interests"] = _split_list(interests)

        goals = _grab(text, ["ищу", "хочу найти", "цель", "мне нужно", "нужно"])
        if goals:
            draft["goals"] = goals.strip()[:200]

        # Свободный рассказ кладём в «О себе», если поле пустое.
        if text and not draft.get("about"):
            draft["about"] = text[:1000]

        return {"draft": draft, "questions": _missing_questions(draft), "provider": self.provider}


class ClaudeAssistant:
    provider = "claude"

    def __init__(self, api_key: str, model: str):
        self.model = model
        from anthropic import Anthropic  # импорт здесь — SDK опционален

        self.client = Anthropic(api_key=api_key)

    def assist(self, text: str, current: dict) -> dict:
        schema_keys = ", ".join(f["key"] for f in PROFILE_FIELDS)
        system = (
            "Ты помощник, который по рассказу пользователя заполняет поля профиля. "
            f"Верни СТРОГО JSON с ключами: {schema_keys}. "
            "skills и interests — массивы строк, остальные — строки. "
            "Не выдумывай факты: если поля нет в рассказе — оставь пустым."
        )
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": f"Текущий профиль: {json.dumps(current, ensure_ascii=False)}\n\nРассказ: {text}"}],
        )
        raw = "".join(block.text for block in msg.content if getattr(block, "type", "") == "text")
        data = json.loads(re.search(r"\{.*\}", raw, re.DOTALL).group(0))
        draft = dict(current)
        for f in PROFILE_FIELDS:
            val = data.get(f["key"])
            if val:
                draft[f["key"]] = val
        return {"draft": draft, "questions": _missing_questions(draft), "provider": self.provider}


class YandexAssistant:
    """YandexGPT через Yandex Cloud Foundation Models. Работает с РФ-сервера без VPN.

    При любой ошибке сети/ключа — мягкий откат на офлайн-помощника, чтобы форма
    всегда отвечала.
    """

    provider = "yandex"

    def __init__(self, api_key: str, folder_id: str, model: str):
        self.api_key = api_key
        self.folder_id = folder_id
        self.model = model

    def assist(self, text: str, current: dict) -> dict:
        import httpx

        schema_keys = ", ".join(f["key"] for f in PROFILE_FIELDS)
        system = (
            "Ты дружелюбный помощник сервиса обмена ресурсами. По рассказу человека "
            "заполни поля профиля и помоги выявить его ресурсы (в т.ч. неочевидные — "
            "прошлый опыт, смежные навыки). "
            f"Верни СТРОГО JSON с ключами: {schema_keys}. "
            "skills и interests — массивы строк, остальные — строки. Не выдумывай факты."
        )
        try:
            resp = httpx.post(
                "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
                headers={"Authorization": f"Api-Key {self.api_key}", "x-folder-id": self.folder_id},
                json={
                    "modelUri": f"gpt://{self.folder_id}/{self.model}/latest",
                    "completionOptions": {"stream": False, "temperature": 0.3, "maxTokens": 1500},
                    "messages": [
                        {"role": "system", "text": system},
                        {"role": "user", "text": f"Текущий профиль: {json.dumps(current, ensure_ascii=False)}\n\nРассказ: {text}"},
                    ],
                },
                timeout=30,
            )
            resp.raise_for_status()
            raw = resp.json()["result"]["alternatives"][0]["message"]["text"]
            data = json.loads(re.search(r"\{.*\}", raw, re.DOTALL).group(0))
            draft = dict(current)
            for f in PROFILE_FIELDS:
                if data.get(f["key"]):
                    draft[f["key"]] = data[f["key"]]
            return {"draft": draft, "questions": _missing_questions(draft), "provider": self.provider}
        except Exception:
            return LocalAssistant().assist(text, current)


def _missing_questions(draft: dict, limit: int = 3) -> list[dict]:
    """Вопросы по незаполненным полям (кроме «О себе» — оно собирается из рассказа)."""
    questions = []
    for f in PROFILE_FIELDS:
        if f["key"] == "about":
            continue
        value = draft.get(f["key"])
        empty = not value or (isinstance(value, list) and len(value) == 0)
        if empty:
            questions.append(
                {"field": f["key"], "question": f"Расскажите про: {f['label'].lower()}?", "examples": f["examples"]}
            )
        if len(questions) >= limit:
            break
    return questions


def get_assistant():
    """Выбрать провайдера: YandexGPT → Claude → офлайн (по наличию ключей)."""
    if settings.yandex_api_key and settings.yandex_folder_id:
        return YandexAssistant(settings.yandex_api_key, settings.yandex_folder_id, settings.yandex_model)
    if settings.anthropic_api_key:
        try:
            return ClaudeAssistant(settings.anthropic_api_key, settings.ai_model)
        except Exception:
            pass
    return LocalAssistant()
