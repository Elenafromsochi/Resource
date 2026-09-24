"""Проверка, что распознавание голоса подключено и работает.

Запуск из папки backend:

    python check_voice.py                      # только проверить настройки
    python check_voice.py путь/к/записи.ogg    # распознать настоящий файл

Первый вызов ничего не тратит: он лишь смотрит, заданы ли ключ и адрес шлюза.
Второй отправляет запись в шлюз — это стоит денег, но копейки.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app import voice                      # noqa: E402
from app.config import settings            # noqa: E402


def mask(value: str) -> str:
    """Показать, что ключ задан, не раскрывая его."""
    if not value:
        return "— не задан"
    return f"задан ({value[:4]}…{value[-3:]}, длина {len(value)})"


def main() -> int:
    print("НАСТРОЙКИ")
    print(f"  адрес шлюза : {settings.transcribe_base_url or '— не задан'}")
    print(f"  ключ        : {mask(settings.transcribe_api_key)}")
    print(f"  модель      : {settings.transcribe_model}")
    print()

    if not voice.is_configured():
        print("Распознавание НЕ подключено.")
        print("Заполните в .env: AI_BASE_URL и AI_API_KEY — те же, что в сервисе «Подари».")
        return 1

    print("Распознавание подключено.")

    if len(sys.argv) < 2:
        print("Чтобы проверить на живой записи, передайте файл:")
        print("  python check_voice.py запись.ogg")
        return 0

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Файла нет: {path}")
        return 1

    suffix = path.suffix.lower().lstrip(".") or "webm"
    print(f"\nОтправляю {path.name} ({path.stat().st_size} байт)…")

    try:
        text = voice.transcribe(path.read_bytes(), f"audio/{suffix}")
    except voice.VoiceError as err:
        print(f"Не получилось: {err}")
        return 1

    if not text:
        print("Шлюз ответил, но текста нет — запись пустая или слишком короткая.")
        return 0

    print(f"\nРаспознано:\n  {text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
