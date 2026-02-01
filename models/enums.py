from __future__ import annotations

import enum


class ResourceType(str, enum.Enum):
    ITEM = "item"
    SERVICE = "service"
    EXPERIENCE = "experience"


class ExchangeType(str, enum.Enum):
    BARTER = "barter"
    MONEY = "money"
    GIFT = "gift"


class ResourceStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class NeedStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class DealStatus(str, enum.Enum):
    DRAFT = "draft"
    SIGNED = "signed"
    TRANSFER = "transfer"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
