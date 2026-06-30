"""Эндпоинты «Даю» (ресурсы) и «Прошу» (потребности) + ИИ-уточнения формы."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..ai import clarifying_questions
from ..auth import get_current_profile
from ..categories import CATEGORIES, category_keys
from ..db import get_db
from ..models import Need, Profile, Resource
from ..schemas import ClarifyIn, NeedOut, ResourceIn, ResourceOut

router = APIRouter(tags=["listings"])


@router.get("/categories")
def list_categories() -> dict:
    """Справочник категорий с полями — для построения формы на клиентах."""
    return CATEGORIES


@router.post("/ai/clarify")
def ai_clarify(body: ClarifyIn) -> dict:
    """До 5 уточняющих вопросов с короткими вариантами ответов."""
    if body.category not in category_keys():
        raise HTTPException(status_code=422, detail="Неизвестная категория")
    return {"questions": clarifying_questions(body.category, body.fields, body.side)}


# --- Ресурсы (Даю) ---
@router.post("/resources", response_model=ResourceOut)
def create_resource(
    body: ResourceIn,
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> Resource:
    if body.category not in category_keys():
        raise HTTPException(status_code=422, detail="Неизвестная категория")
    resource = Resource(
        owner_id=profile.id,
        category=body.category,
        title=body.title,
        description=body.description,
        location=body.location,
        fields=body.fields,
        ideal_for=body.ideal_for,
    )
    db.add(resource)
    # «Даю» — самостоятельный акт. Баланс — мягкий индикатор.
    profile.give_count += 1
    db.add(profile)
    db.commit()
    db.refresh(resource)
    return resource


@router.get("/resources", response_model=list[ResourceOut])
def list_resources(
    category: str | None = None,
    mine: bool = False,
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> list[Resource]:
    stmt = select(Resource).where(Resource.status == "active")
    if category:
        stmt = stmt.where(Resource.category == category)
    if mine:
        stmt = stmt.where(Resource.owner_id == profile.id)
    return list(db.scalars(stmt.order_by(Resource.created_at.desc())))


# --- Потребности (Прошу) ---
@router.post("/needs", response_model=NeedOut)
def create_need(
    body: ResourceIn,
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> Need:
    if body.category not in category_keys():
        raise HTTPException(status_code=422, detail="Неизвестная категория")
    need = Need(
        owner_id=profile.id,
        category=body.category,
        title=body.title,
        description=body.description,
        location=body.location,
        fields=body.fields,
    )
    db.add(need)
    profile.ask_count += 1  # независимо от give_count
    db.add(profile)
    db.commit()
    db.refresh(need)
    return need


@router.get("/needs", response_model=list[NeedOut])
def list_needs(
    category: str | None = None,
    mine: bool = False,
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> list[Need]:
    stmt = select(Need).where(Need.status == "active")
    if category:
        stmt = stmt.where(Need.category == category)
    if mine:
        stmt = stmt.where(Need.owner_id == profile.id)
    return list(db.scalars(stmt.order_by(Need.created_at.desc())))
