from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base
from models.enums import DealStatus


class Deal(Base):
    __tablename__ = "deals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resource_id: Mapped[int] = mapped_column(ForeignKey("resources.id"), index=True)
    need_id: Mapped[int] = mapped_column(ForeignKey("needs.id"), index=True)
    participant_a_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    participant_b_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[DealStatus] = mapped_column(Enum(DealStatus), default=DealStatus.DRAFT)
    contract_text: Mapped[str | None] = mapped_column(Text)
    chat_history: Mapped[list] = mapped_column(JSONB, default=list)
    match_score: Mapped[int | None] = mapped_column(Integer)
    signed_by_a: Mapped[bool] = mapped_column(Boolean, default=False)
    signed_by_b: Mapped[bool] = mapped_column(Boolean, default=False)
    transfer_by_a: Mapped[bool] = mapped_column(Boolean, default=False)
    transfer_by_b: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    resource = relationship("Resource", back_populates="deals")
    need = relationship("Need", back_populates="deals")
