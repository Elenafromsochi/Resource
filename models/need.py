from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base
from models.enums import ExchangeType, NeedStatus, ResourceType


class Need(Base):
    __tablename__ = "needs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(120))
    deadline: Mapped[str | None] = mapped_column(String(120))
    location: Mapped[str | None] = mapped_column(String(255))
    conditions: Mapped[str | None] = mapped_column(String(255))
    format_type: Mapped[ResourceType | None] = mapped_column(Enum(ResourceType))
    exchange_type: Mapped[ExchangeType | None] = mapped_column(Enum(ExchangeType))
    status: Mapped[NeedStatus] = mapped_column(
        Enum(NeedStatus), default=NeedStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="needs")
    deals = relationship("Deal", back_populates="need")
