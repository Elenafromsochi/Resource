"""Тесты личного кабинета и ИИ-помощника (офлайн-провайдер)."""

from app.ai import LocalAssistant
from tests.conftest import auth_headers


def test_local_assistant_extracts_fields():
    a = LocalAssistant()
    text = (
        "Меня зовут Анна Иванова. Живу в Сочи, работаю дизайнером. "
        "Умею вёрстка, фотография и ретушь. Увлекаюсь спортом, музыкой. Ищу новые проекты."
    )
    out = a.assist(text, {"full_name": "", "occupation": "", "city": "", "about": "",
                          "skills": [], "interests": [], "goals": "", "contacts": ""})
    draft = out["draft"]
    assert draft["full_name"].startswith("Анна")
    assert draft["city"] == "Сочи"
    assert "дизайнер" in draft["occupation"].lower()
    assert "вёрстка" in [s.lower() for s in draft["skills"]]
    assert len(draft["interests"]) >= 2
    assert "проект" in draft["goals"].lower()
    assert draft["about"]  # свободный рассказ попал в «о себе»
    assert out["provider"] == "local"


def test_local_assistant_asks_for_missing():
    a = LocalAssistant()
    out = a.assist("Просто хочу зарегистрироваться", {"full_name": "", "occupation": "",
                   "city": "", "about": "", "skills": [], "interests": [], "goals": "", "contacts": ""})
    fields = {q["field"] for q in out["questions"]}
    assert "full_name" in fields  # имя не указано — спрашиваем
    assert len(out["questions"]) <= 3


def test_assist_endpoint_does_not_overwrite_until_saved(client):
    headers = auth_headers(client, "kab@b.ru")
    # ИИ предлагает черновик.
    resp = client.post("/api/profile/assist", headers=headers,
                       json={"text": "Меня зовут Пётр. Живу в Москве."}).json()
    assert resp["draft"]["full_name"].startswith("Пётр")
    assert resp["draft"]["city"] == "Москве" or resp["draft"]["city"] == "Москва"
    assert resp["provider"] == "local"
    # Профиль ещё не изменён — assist возвращает только черновик.
    assert client.get("/api/profile", headers=headers).json()["full_name"] == ""

    # Сохраняем через PUT.
    saved = client.put("/api/profile", headers=headers, json=resp["draft"]).json()
    assert saved["full_name"].startswith("Пётр")
    assert saved["completeness"] > 0


def test_update_profile_roundtrip(client):
    headers = auth_headers(client, "rt@b.ru")
    body = {"full_name": "Ира", "occupation": "репетитор", "city": "Казань", "about": "люблю учить",
            "skills": ["математика"], "interests": ["шахматы"], "goals": "ученики", "contacts": "@ira"}
    saved = client.put("/api/profile", headers=headers, json=body).json()
    assert saved["skills"] == ["математика"]
    assert saved["completeness"] == 1.0  # все учитываемые поля заполнены
