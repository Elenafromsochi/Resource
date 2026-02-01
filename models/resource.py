from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base
from models.enums import ExchangeType, ResourceStatus, ResourceType


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    resource_type: Mapped[ResourceType] = mapped_column(
        Enum(ResourceType), default=ResourceType.ITEM
    )
    description: Mapped[str] = mapped_column(Text)
    time_info: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(120))
    condition: Mapped[str | None] = mapped_column(String(120))
    estimated_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    exchange_type: Mapped[ExchangeType | None] = mapped_column(Enum(ExchangeType))
    photo_file_id: Mapped[str | None] = mapped_column(String(255))
    link: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[ResourceStatus] = mapped_column(
        Enum(ResourceStatus), default=ResourceStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="resources")
    deals = relationship("Deal", back_populates="resource")
