from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    rating_score: Mapped[float] = mapped_column(Float, default=5.0)
    gifts_given: Mapped[int] = mapped_column(Integer, default=0)
    gifts_received: Mapped[int] = mapped_column(Integer, default=0)
    gift_balance: Mapped[int] = mapped_column(Integer, default=0)
    is_active_member: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    resources = relationship("Resource", back_populates="owner")
    needs = relationship("Need", back_populates="owner")
