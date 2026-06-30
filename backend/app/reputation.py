"""Капитал доверия и уровни профиля.

Формула (из брифа): репутация = оценка × коэффициент отзывов.
Привилегии «органического» уровня даются за рейтинг (не за подписку).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import LEVEL_HIGH, LEVEL_LIGHT, LEVEL_MEDIUM, Profile, Review


def level_for(trust_capital: float) -> str:
    if trust_capital >= 75:
        return LEVEL_HIGH
    if trust_capital >= 50:
        return LEVEL_MEDIUM
    return LEVEL_LIGHT


def recompute_trust(db: Session, profile_id: str) -> float:
    """Пересчитать капитал доверия по отзывам о пользователе."""
    reviews = db.scalars(select(Review).where(Review.subject_id == profile_id)).all()
    profile = db.get(Profile, profile_id)
    if profile is None:
        return 0.0
    if not reviews:
        profile.trust_capital = 50.0  # стартовая нейтральная репутация
    else:
        # Средняя оценка (0..100) скорректированная средним коэффициентом отзывов.
        avg_rating = sum(r.rating for r in reviews) / len(reviews)  # 1..5
        avg_coef = sum(r.coefficient for r in reviews) / len(reviews)
        trust = (avg_rating / 5.0) * 100.0 * avg_coef
        profile.trust_capital = max(0.0, min(100.0, round(trust, 1)))
    profile.level = level_for(profile.trust_capital)
    db.add(profile)
    return profile.trust_capital
