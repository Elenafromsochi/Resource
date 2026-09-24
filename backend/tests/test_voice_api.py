"""Проверки ручки голосового ввода. Шлюз не дёргается — денег не тратим."""

from __future__ import annotations

from app import voice
from tests.conftest import auth_headers


def _audio(size: int = 5000) -> dict:
    return {"file": ("voice.ogg", b"x" * size, "audio/ogg")}


def test_чужому_голос_недоступен(client):
    """Без токена ручка не должна работать: распознавание стоит денег."""
    assert client.post("/api/voice/transcribe", files=_audio()).status_code == 401
    assert client.get("/api/voice/status").status_code == 401


def test_статус_говорит_правду_о_подключении(client):
    headers = auth_headers(client, "voice-status@test.ru")
    body = client.get("/api/voice/status", headers=headers).json()
    # В тестах ключа нет, значит и голос выключен — кабинет спрячет микрофон.
    assert body == {"enabled": False}


def test_случайное_нажатие_не_ошибка(client):
    """Полсекунды тишины — это не сбой, человеку ничего сообщать не надо."""
    headers = auth_headers(client, "voice-silence@test.ru")
    r = client.post("/api/voice/transcribe", headers=headers, files=_audio(300))
    assert r.status_code == 200
    assert r.json() == {"text": ""}


def test_длинная_запись_отклоняется_понятным_текстом(client):
    headers = auth_headers(client, "voice-long@test.ru")
    r = client.post("/api/voice/transcribe", headers=headers, files=_audio(voice.MAX_AUDIO_BYTES + 10))
    assert r.status_code == 413
    assert "короче" in r.json()["detail"]


def test_без_ключа_объясняем_причину(client):
    headers = auth_headers(client, "voice-nokey@test.ru")
    r = client.post("/api/voice/transcribe", headers=headers, files=_audio())
    assert r.status_code == 503
    assert "не подключено" in r.json()["detail"]


def test_с_ключом_возвращается_распознанный_текст(client, monkeypatch):
    """Ответ шлюза подменяем: проверяем свой путь, а не чужой сервис."""

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"text": "нужно перевезти диван в субботу"}

    monkeypatch.setattr(voice.settings, "transcribe_api_key", "test-key", raising=False)
    monkeypatch.setattr(voice.settings, "transcribe_base_url", "https://gateway.test/v1", raising=False)
    monkeypatch.setattr(voice.httpx, "post", lambda *a, **kw: FakeResponse())

    headers = auth_headers(client, "voice-ok@test.ru")
    assert client.get("/api/voice/status", headers=headers).json() == {"enabled": True}

    r = client.post("/api/voice/transcribe", headers=headers, files=_audio())
    assert r.status_code == 200
    assert r.json() == {"text": "нужно перевезти диван в субботу"}
