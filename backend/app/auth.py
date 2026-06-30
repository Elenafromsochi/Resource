"""Авторизация: общий механизм, разные инструменты.

Сайт (без VPN)      → вход по логину/паролю, JWT.
Telegram Mini App   → вход по initData (HMAC-проверка по токену бота).
VK / Supabase        → точки расширения (тот же адаптер выдаёт JWT).

JWT и хэш пароля реализованы на стандартной библиотеке, чтобы прототип
запускался и тестировался без внешних зависимостей.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import Profile


# --- Пароли (PBKDF2) ---
def hash_password(password: str) -> str:
    salt = hashlib.sha256(settings.jwt_secret.encode()).digest()[:16]
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return dk.hex()


def verify_password(password: str, hashed: str) -> bool:
    return hmac.compare_digest(hash_password(password), hashed or "")


# --- JWT (HS256, self-contained) ---
def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def create_token(profile_id: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": profile_id, "exp": int(time.time()) + settings.jwt_ttl_seconds}
    segments = [
        _b64url(json.dumps(header, separators=(",", ":")).encode()),
        _b64url(json.dumps(payload, separators=(",", ":")).encode()),
    ]
    signing_input = ".".join(segments).encode()
    sig = hmac.new(settings.jwt_secret.encode(), signing_input, hashlib.sha256).digest()
    segments.append(_b64url(sig))
    return ".".join(segments)


def decode_token(token: str) -> dict:
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
    except ValueError as exc:
        raise ValueError("malformed token") from exc
    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected = hmac.new(settings.jwt_secret.encode(), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, _b64url_decode(sig_b64)):
        raise ValueError("bad signature")
    payload = json.loads(_b64url_decode(payload_b64))
    if payload.get("exp", 0) < int(time.time()):
        raise ValueError("expired")
    return payload


# --- Telegram WebApp initData ---
def verify_telegram_init_data(init_data: str, bot_token: str) -> dict:
    """Проверка подписи initData по алгоритму Telegram. Возвращает поле user (dict)."""
    if not bot_token:
        raise ValueError("telegram bot token not configured")
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise ValueError("no hash in init_data")
    data_check_string = "\n".join(f"{k}={pairs[k]}" for k in sorted(pairs))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calc_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calc_hash, received_hash):
        raise ValueError("bad init_data signature")
    user_raw = pairs.get("user")
    return json.loads(user_raw) if user_raw else {}


# --- Зависимость текущего пользователя ---
def get_current_profile(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
) -> Profile:
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Нет токена")
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный токен")
    profile = db.get(Profile, payload["sub"])
    if profile is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Профиль не найден")
    return profile
