"""Регистрация и вход: по email/паролю и через Яндекс ID (OAuth)."""

from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import create_token, hash_password, verify_password
from ..config import settings
from ..db import get_db
from ..models import Profile, User
from ..schemas import LoginIn, RegisterIn, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, db: Session = Depends(get_db)) -> TokenOut:
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email уже зарегистрирован")
    user = User(email=email, password_hash=hash_password(body.password))
    user.profile = Profile()  # пустой кабинет создаётся сразу
    db.add(user)
    db.commit()
    return TokenOut(access_token=create_token(user.id))


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль")
    return TokenOut(access_token=create_token(user.id))


# --- Вход через Яндекс ID (OAuth 2.0, authorization code) ---

def _site_base(request: Request) -> str:
    """Публичный адрес сайта. Берём PUBLIC_URL, иначе — из заголовков запроса
    (учитывая обратный прокси Timeweb: X-Forwarded-Proto/Host)."""
    if settings.public_url:
        return settings.public_url
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
    return f"{proto}://{host}"


def _redirect_uri(request: Request) -> str:
    return f"{_site_base(request)}/api/auth/yandex/callback"


@router.get("/yandex/login", include_in_schema=False)
def yandex_login(request: Request) -> RedirectResponse:
    """Отправляем пользователя на страницу разрешения Яндекса."""
    if not settings.yandex_login_enabled:
        raise HTTPException(status_code=503, detail="Вход через Яндекс не настроен")
    params = urlencode({
        "response_type": "code",
        "client_id": settings.yandex_oauth_client_id,
        "redirect_uri": _redirect_uri(request),
    })
    return RedirectResponse(f"https://oauth.yandex.ru/authorize?{params}")


@router.get("/yandex/callback", include_in_schema=False)
def yandex_callback(request: Request, code: str = "", db: Session = Depends(get_db)) -> RedirectResponse:
    """Яндекс вернул код → меняем на токен, узнаём пользователя, выдаём свой JWT."""
    base = _site_base(request)
    if not settings.yandex_login_enabled:
        return RedirectResponse(f"{base}/?auth_error=" + urlencode({"": "not_configured"})[1:])
    if not code:
        return RedirectResponse(f"{base}/?auth_error=canceled")

    import httpx

    try:
        token_resp = httpx.post(
            "https://oauth.yandex.ru/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": settings.yandex_oauth_client_id,
                "client_secret": settings.yandex_oauth_client_secret,
                "redirect_uri": _redirect_uri(request),
            },
            timeout=20,
        )
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]

        info = httpx.get(
            "https://login.yandex.ru/info",
            params={"format": "json"},
            headers={"Authorization": f"OAuth {access_token}"},
            timeout=20,
        )
        info.raise_for_status()
        data = info.json()
    except Exception:
        return RedirectResponse(f"{base}/?auth_error=yandex")

    yid = str(data.get("id") or "")
    email = (data.get("default_email") or "").lower()
    if not email:
        emails = data.get("emails") or []
        email = (emails[0] if emails else f"ya{yid}@yandex").lower()
    name = data.get("real_name") or data.get("display_name") or ""

    # Находим по yandex_id, затем по email (связываем с существующим аккаунтом), иначе создаём.
    user = db.scalar(select(User).where(User.yandex_id == yid)) if yid else None
    if user is None:
        user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, password_hash="", yandex_id=yid or None)
        user.profile = Profile(full_name=name)
        db.add(user)
    else:
        if yid and not user.yandex_id:
            user.yandex_id = yid
        if user.profile is None:
            user.profile = Profile(full_name=name)
        elif name and not user.profile.full_name:
            user.profile.full_name = name
    db.commit()

    return RedirectResponse(f"{base}/?token={create_token(user.id)}")
