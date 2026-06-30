"""Сквозной тест: форма → мэтчинг → договор в чате → завершение → отзыв."""

from tests.conftest import auth_headers


def _me(client, headers):
    return client.get("/api/auth/me", headers=headers).json()


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_categories_exposed(client):
    cats = client.get("/api/categories").json()
    assert set(cats) == {"time_skill", "thing", "space", "knowledge"}


def test_ai_clarify_returns_questions(client):
    resp = client.post(
        "/api/ai/clarify",
        json={"category": "thing", "side": "give", "fields": {}},
    ).json()
    assert 1 <= len(resp["questions"]) <= 5
    # Ресурсодателю дополнительно задаётся вопрос «кому идеально подойдёт».
    assert any(q["field"] == "ideal_for" for q in resp["questions"])
    # Стороне «Прошу» этот вопрос не задаётся.
    ask = client.post(
        "/api/ai/clarify",
        json={"category": "thing", "side": "ask", "fields": {}},
    ).json()
    assert not any(q["field"] == "ideal_for" for q in ask["questions"])


def test_full_deal_flow(client):
    giver = auth_headers(client, "giver")
    taker = auth_headers(client, "taker")
    giver_id = _me(client, giver)["id"]
    taker_id = _me(client, taker)["id"]

    # Даю — ресурс.
    resource = client.post(
        "/api/resources",
        headers=giver,
        json={
            "category": "time_skill",
            "title": "Помогу с переездом",
            "location": "Москва",
            "fields": {
                "qualification": "advanced",
                "availability": ["выходные"],
                "transfer_terms": ["gift", "barter"],
            },
            "ideal_for": "Тем, кто переезжает по городу",
        },
    ).json()

    # Прошу — потребность (зеркальная, совместимая).
    need = client.post(
        "/api/needs",
        headers=taker,
        json={
            "category": "time_skill",
            "title": "Нужна помощь с переездом",
            "location": "Москва",
            "fields": {
                "qualification": "intermediate",
                "availability": ["выходные"],
                "transfer_terms": ["gift"],
            },
        },
    ).json()

    # Баланс даю/прошу — независимые счётчики.
    assert _me(client, giver)["give_count"] == 1
    assert _me(client, taker)["ask_count"] == 1

    # Зеркальный мэтчинг находит пару выше порога.
    matches = client.get(f"/api/matches/for-need/{need['id']}", headers=taker).json()
    assert matches and matches[0]["resource_id"] == resource["id"]
    assert matches[0]["is_match"] is True

    # Открываем сделку.
    deal = client.post(
        "/api/deals",
        headers=taker,
        json={"resource_id": resource["id"], "counterparty_id": taker_id},
    ).json()
    assert deal["giver_id"] == giver_id and deal["taker_id"] == taker_id
    assert any(m["role"] == "bot_mediator" for m in deal["messages"])

    # Договор собирается прямо в чате репликами «Поле: значение».
    for label, value in [
        ("Суть", "Переезд в субботу"),
        ("Критерии качества", "Вещи целы, уложились в 3 часа"),
        ("План Б", "Переносим на воскресенье"),
        ("Декларация", "Действуем добросовестно"),
    ]:
        deal = client.post(
            f"/api/deals/{deal['id']}/messages",
            headers=taker,
            json={"text": f"{label}: {value}"},
        ).json()
    assert deal["contract_completeness"] == 1.0

    # Подписывают обе стороны.
    client.post(f"/api/deals/{deal['id']}/sign", headers=taker)
    deal = client.post(f"/api/deals/{deal['id']}/sign", headers=giver).json()
    assert deal["signed_by_all"] is True and deal["status"] == "signed"

    # Завершение → акт + STAR-черновик.
    completed = client.post(f"/api/deals/{deal['id']}/complete", headers=giver).json()
    act_id = completed["act_id"]
    assert completed["star_draft"]["situation"] == "Переезд в субботу"

    # Отзыв STAR от taker про giver поднимает капитал доверия.
    before = _me(client, giver)["trust_capital"]
    review = client.post(
        f"/api/deals/acts/{act_id}/review",
        headers=taker,
        json={
            "situation": "Переезд",
            "task": "Перевезти вещи",
            "action": "Помог упаковать и перевезти",
            "result": "Всё цело",
            "rating": 5,
        },
    ).json()
    assert review["subject_id"] == giver_id
    assert review["subject_trust_capital"] > before


def test_signing_requires_full_contract(client):
    giver = auth_headers(client, "giver2")
    taker = auth_headers(client, "taker2")
    taker_id = _me(client, taker)["id"]
    resource = client.post(
        "/api/resources",
        headers=giver,
        json={"category": "thing", "title": "Велосипед", "location": "Москва",
              "fields": {"transfer_terms": ["gift"]}},
    ).json()
    deal = client.post(
        "/api/deals", headers=giver,
        json={"resource_id": resource["id"], "counterparty_id": taker_id},
    ).json()
    # Договор пустой — подпись отклоняется.
    resp = client.post(f"/api/deals/{deal['id']}/sign", headers=giver)
    assert resp.status_code == 422
