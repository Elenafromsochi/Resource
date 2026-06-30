"""Тесты регистрации и входа."""

from tests.conftest import auth_headers


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_register_and_login(client):
    r = client.post("/api/auth/register", json={"email": "a@b.ru", "password": "secret1"})
    assert r.status_code == 201
    assert r.json()["access_token"]

    # Повторная регистрация — конфликт.
    assert client.post("/api/auth/register", json={"email": "a@b.ru", "password": "secret1"}).status_code == 409

    # Вход с верным паролем.
    assert client.post("/api/auth/login", json={"email": "a@b.ru", "password": "secret1"}).status_code == 200
    # Неверный пароль.
    assert client.post("/api/auth/login", json={"email": "a@b.ru", "password": "wrong"}).status_code == 401


def test_short_password_rejected(client):
    assert client.post("/api/auth/register", json={"email": "x@y.ru", "password": "123"}).status_code == 422


def test_profile_requires_auth(client):
    assert client.get("/api/profile").status_code == 401


def test_new_profile_is_empty(client):
    headers = auth_headers(client, "fresh@b.ru")
    p = client.get("/api/profile", headers=headers).json()
    assert p["email"] == "fresh@b.ru"
    assert p["completeness"] == 0.0
    assert p["skills"] == []
