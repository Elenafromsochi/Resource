"""Распознавание голоса: аудио → текст.

Схема перенесена из сервиса «Подари», где она уже работает в проде. Код там
на TypeScript, поэтому скопировать его нельзя — повторён сам вызов, а он
простой: обычный OpenAI-совместимый `/audio/transcriptions`, модель whisper-1,
язык русский.

ПОЧЕМУ ЭТОТ ПУТЬ, А НЕ OPENAI НАПРЯМУЮ. В «Подари» шлюзом стоит ProxyAPI —
российский посредник к тем же моделям. Он работает с РФ-сервера без VPN и
оплачивается рублями. Ключ и шлюз у сервиса уже есть, так что здесь ничего
покупать заново не нужно: те же переменные окружения подходят как есть.

Ограничения взяты оттуда же и проверены жизнью:
  • меньше 1200 байт — это тишина, в модель не отправляем и денег не тратим;
  • больше ~6 МБ — длиннее, чем нужно для реплики в разговоре;
  • распознанный текст режется и проверяется на попытку подмены инструкций:
    человек (или тот, кто пришлёт ему голосовое) может надиктовать
    «игнорируй предыдущие указания», и этот текст попадёт прямо в промпт.
"""

from __future__ import annotations

import re

import httpx

from .config import settings


# Максимум того, что имеет смысл распознавать: реплика, а не лекция.
MAX_AUDIO_BYTES = 6 * 1024 * 1024
# Меньше этого — почти наверняка случайное нажатие или тишина.
MIN_AUDIO_BYTES = 1200
# Длиннее одной реплики нам не нужно, а в промпт лишнее не тащим.
MAX_TEXT_CHARS = 1500

# Та же проверка, что стоит в «Подари»: ловит попытку перехватить инструкции.
_UNSAFE = re.compile(r"(system\s*:|<\|[^|]*\|>|ignore (all |the )?(previous|above))", re.IGNORECASE)

# Telegram присылает голосовые в ogg/opus, браузер — обычно webm.
_EXTENSIONS = (
    ("webm", "webm"),
    ("ogg", "ogg"),
    ("oga", "ogg"),
    ("opus", "ogg"),
    ("mp4", "mp4"),
    ("m4a", "mp4"),
    ("aac", "mp4"),
    ("wav", "wav"),
    ("mpeg", "mp3"),
    ("mp3", "mp3"),
)


class VoiceError(RuntimeError):
    """Распознать не удалось. Сообщение написано так, чтобы показать человеку."""


def _extension(mime_type: str) -> str:
    mime = (mime_type or "").lower()
    for marker, ext in _EXTENSIONS:
        if marker in mime:
            return ext
    return "webm"


def looks_unsafe(text: str) -> bool:
    """Похоже ли, что в тексте прячется попытка подменить инструкции."""
    return bool(_UNSAFE.search(text))


def is_configured() -> bool:
    """Подключено ли распознавание. Если нет — интерфейс не показывает микрофон."""
    return bool(settings.transcribe_api_key and settings.transcribe_base_url)


def transcribe(audio: bytes, mime_type: str = "audio/webm", *, timeout: float = 60.0) -> str:
    """Аудио → текст. Пустая строка означает «там тишина», а не ошибку.

    :raises VoiceError: распознавание не подключено, запись слишком большая
        или шлюз ответил ошибкой.
    """
    # Сначала о самой записи, и только потом о настройках: случайное нажатие
    # микрофона — это тишина, а не повод рассказывать человеку про ключи.
    if not audio or len(audio) < MIN_AUDIO_BYTES:
        return ""

    if len(audio) > MAX_AUDIO_BYTES:
        raise VoiceError("Запись слишком длинная. Скажите короче — одной репликой.")

    if not is_configured():
        raise VoiceError("Распознавание речи не подключено: нужен AI_API_KEY и AI_BASE_URL.")

    files = {"file": (f"voice.{_extension(mime_type)}", audio, mime_type or "audio/webm")}
    data = {"model": settings.transcribe_model, "language": "ru"}
    headers = {"Authorization": f"Bearer {settings.transcribe_api_key}"}
    url = f"{settings.transcribe_base_url.rstrip('/')}/audio/transcriptions"

    try:
        response = httpx.post(url, files=files, data=data, headers=headers, timeout=timeout)
    except httpx.HTTPError as err:
        raise VoiceError("Сервис распознавания не отвечает. Попробуйте ещё раз или напишите текстом.") from err

    if response.status_code != 200:
        # Тело ответа шлюза в сообщение человеку не выносим — только в лог.
        raise VoiceError(f"Распознать не удалось (код {response.status_code}). Напишите текстом, пожалуйста.")

    text = str(response.json().get("text", "")).strip()[:MAX_TEXT_CHARS]
    return "" if looks_unsafe(text) else text
