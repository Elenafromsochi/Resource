"""Тесты нормализации строки подключения к БД и справочных эндпоинтов."""

from app.config import _normalize_db_url
from tests.conftest import auth_headers


def test_postgres_scheme_normalized():
    assert _normalize_db_url("postgres://u:p@host:5432/db") == "postgresql://u:p@host:5432/db"


def test_verify_full_downgraded_and_rootcert_dropped():
    url = "postgresql://u:p@host:5432/db?sslmode=verify-full&sslrootcert=root.crt"
    out = _normalize_db_url(url)
    assert "sslmode=require" in out
    assert "verify-full" not in out
    assert "sslrootcert" not in out


def test_sqlite_untouched():
    assert _normalize_db_url("sqlite:///./resurs.db") == "sqlite:///./resurs.db"


def test_questions_endpoint(client):
    data = client.get("/api/questions").json()
    assert len(data["questions"]) >= 5
    assert all("id" in q and "text" in q for q in data["questions"])


def test_answers_saved_in_profile(client):
    headers = auth_headers(client, "answers@b.ru")
    body = {"full_name": "Тест", "answers": {"give": "консультации", "need": "ноутбук"}}
    saved = client.put("/api/profile", headers=headers, json=body).json()
    assert saved["answers"]["give"] == "консультации"
    # ответы сохраняются и читаются обратно
    again = client.get("/api/profile", headers=headers).json()
    assert again["answers"]["need"] == "ноутбук"
