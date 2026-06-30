"""Эндпоинты авторизации: сайт (пароль) и Telegram Mini App (initData)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import (
    create_token,
    get_current_profile,
    hash_password,
    verify_password,
    verify_telegram_init_data,
)
from ..config import settings
from ..db import get_db
from ..models import Profile
from ..schemas import LoginIn, ProfileOut, RegisterIn, TelegramAuthIn, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut)
def register(body: RegisterIn, db: Session = Depends(get_db)) -> TokenOut:
    exists = db.scalar(select(Profile).where(Profile.username == body.username))
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Логин занят")
    profile = Profile(
        auth_provider="password",
        username=body.username,
        display_name=body.display_name or body.username,
        password_hash=hash_password(body.password),
    )
    db.add(profile)
    db.commit()
    return TokenOut(access_token=create_token(profile.id))


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    profile = db.scalar(select(Profile).where(Profile.username == body.username))
    if profile is None or not verify_password(body.password, profile.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль")
    return TokenOut(access_token=create_token(profile.id))


@router.post("/telegram", response_model=TokenOut)
def telegram(body: TelegramAuthIn, db: Session = Depends(get_db)) -> TokenOut:
    """Вход из Telegram Mini App по initData (тот же механизм, другой инструмент)."""
    try:
        user = verify_telegram_init_data(body.init_data, settings.telegram_bot_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    tg_id = str(user.get("id"))
    profile = db.scalar(
        select(Profile).where(Profile.auth_provider == "telegram", Profile.external_id == tg_id)
    )
    if profile is None:
        profile = Profile(
            auth_provider="telegram",
            external_id=tg_id,
            display_name=user.get("first_name", "Гость"),
        )
        db.add(profile)
        db.commit()
    return TokenOut(access_token=create_token(profile.id))


@router.get("/me", response_model=ProfileOut)
def me(profile: Profile = Depends(get_current_profile)) -> Profile:
    return profile
