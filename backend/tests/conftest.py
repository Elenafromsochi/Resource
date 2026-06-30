import os
import tempfile

# Изолированная файловая SQLite-БД на каждый прогон тестов (до импорта app).
_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["TELEGRAM_BOT_TOKEN"] = "test:token"

import pytest
from fastapi.testclient import TestClient

from app.db import init_db
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def _setup_db():
    init_db()
    yield
    os.close(_db_fd)
    os.unlink(_db_path)


@pytest.fixture
def client():
    return TestClient(app)


def auth_headers(client, username, password="pass12345"):
    client.post("/api/auth/register", json={"username": username, "password": password})
    token = client.post(
        "/api/auth/login", json={"username": username, "password": password}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
