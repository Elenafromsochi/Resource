"""Личный кабинет: просмотр, сохранение и заполнение с помощью ИИ."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..ai import PROFILE_FIELDS, get_assistant
from ..auth import get_current_user
from ..db import get_db
from ..models import Profile, User
from ..schemas import AssistIn, AssistOut, ProfileData, ProfileOut

router = APIRouter(prefix="/profile", tags=["profile"])

# Поля, учитываемые в проценте заполнения (без «контактов» — необязательно).
_SCORED = [f["key"] for f in PROFILE_FIELDS if f["key"] != "contacts"]


def _ensure_profile(user: User, db: Session) -> Profile:
    if user.profile is None:
        user.profile = Profile()
        db.add(user)
        db.commit()
    return user.profile


def _completeness(p: Profile) -> float:
    filled = 0
    for key in _SCORED:
        value = getattr(p, key)
        if value and (not isinstance(value, list) or len(value) > 0):
            filled += 1
    return round(filled / len(_SCORED), 2)


def _to_out(user: User, p: Profile) -> ProfileOut:
    return ProfileOut(
        email=user.email,
        full_name=p.full_name,
        occupation=p.occupation,
        city=p.city,
        about=p.about,
        skills=p.skills or [],
        interests=p.interests or [],
        goals=p.goals,
        contacts=p.contacts,
        answers=p.answers or {},
        completeness=_completeness(p),
    )


@router.get("", response_model=ProfileOut)
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ProfileOut:
    return _to_out(user, _ensure_profile(user, db))


@router.put("", response_model=ProfileOut)
def update_profile(
    body: ProfileData,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileOut:
    p = _ensure_profile(user, db)
    p.full_name = body.full_name
    p.occupation = body.occupation
    p.city = body.city
    p.about = body.about
    p.skills = body.skills
    p.interests = body.interests
    p.goals = body.goals
    p.contacts = body.contacts
    p.answers = body.answers
    db.add(p)
    db.commit()
    db.refresh(p)
    return _to_out(user, p)


@router.post("/assist", response_model=AssistOut)
def assist(
    body: AssistIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AssistOut:
    """ИИ раскладывает рассказ по полям и подсказывает, чего ещё не хватает.

    Возвращает черновик (его можно отредактировать на клиенте и сохранить через PUT) —
    сам по себе профиль не перезаписывает.
    """
    p = _ensure_profile(user, db)
    current = ProfileData(
        full_name=p.full_name, occupation=p.occupation, city=p.city, about=p.about,
        skills=p.skills or [], interests=p.interests or [], goals=p.goals, contacts=p.contacts,
    ).model_dump()
    result = get_assistant().assist(body.text, current)
    return AssistOut(
        draft=ProfileData(**result["draft"]),
        questions=result["questions"],
        provider=result["provider"],
    )
