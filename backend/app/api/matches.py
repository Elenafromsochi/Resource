"""Зеркальный мэтчинг: подобрать ресурсы под потребность и наоборот."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import get_current_profile
from ..config import settings
from ..db import get_db
from ..matching import is_match, match_score
from ..models import Need, Profile, Resource
from ..schemas import MatchOut

router = APIRouter(prefix="/matches", tags=["matches"])


def _to_dict(obj) -> dict:
    return {"category": obj.category, "location": obj.location, "fields": obj.fields or {}}


@router.get("/for-need/{need_id}", response_model=list[MatchOut])
def matches_for_need(
    need_id: str,
    threshold: float | None = None,
    _: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> list[MatchOut]:
    need = db.get(Need, need_id)
    if need is None:
        raise HTTPException(status_code=404, detail="Потребность не найдена")
    thr = settings.match_threshold if threshold is None else threshold
    results: list[MatchOut] = []
    resources = db.scalars(select(Resource).where(Resource.status == "active")).all()
    for res in resources:
        giver = db.get(Profile, res.owner_id)
        trust = giver.trust_capital if giver else 50.0
        score = match_score(_to_dict(res), _to_dict(need), trust)
        if score is None:
            continue
        results.append(
            MatchOut(resource_id=res.id, need_id=need.id, score=score, is_match=is_match(score, thr))
        )
    results.sort(key=lambda m: m.score, reverse=True)
    return results


@router.get("/for-resource/{resource_id}", response_model=list[MatchOut])
def matches_for_resource(
    resource_id: str,
    threshold: float | None = None,
    _: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> list[MatchOut]:
    resource = db.get(Resource, resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="Ресурс не найден")
    giver = db.get(Profile, resource.owner_id)
    trust = giver.trust_capital if giver else 50.0
    thr = settings.match_threshold if threshold is None else threshold
    results: list[MatchOut] = []
    needs = db.scalars(select(Need).where(Need.status == "active")).all()
    for need in needs:
        score = match_score(_to_dict(resource), _to_dict(need), trust)
        if score is None:
            continue
        results.append(
            MatchOut(resource_id=resource.id, need_id=need.id, score=score, is_match=is_match(score, thr))
        )
    results.sort(key=lambda m: m.score, reverse=True)
    return results
