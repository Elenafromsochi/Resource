from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

import redis.asyncio as redis

from models.enums import ExchangeType, ResourceType
from models.need import Need
from models.resource import Resource


@dataclass(slots=True)
class MatchResult:
    need: Need
    score: int


class MatchEngine:
    def __init__(self, redis_url: str, threshold: int = 80) -> None:
        self.threshold = threshold
        self._redis = redis.from_url(redis_url, decode_responses=True)

    async def close(self) -> None:
        await self._redis.close()

    async def enqueue_match(self, kind: str, entity_id: int) -> None:
        await self._redis.lpush("match_queue", f"{kind}:{entity_id}")

    def _similarity(self, left: str, right: str) -> float:
        return SequenceMatcher(None, left.lower(), right.lower()).ratio()

    def _match_exchange(
        self, left: ExchangeType | None, right: ExchangeType | None
    ) -> float:
        if not left or not right:
            return 0.0
        return 1.0 if left == right else 0.0

    def _match_format(
        self, left: ResourceType | None, right: ResourceType | None
    ) -> float:
        if not left or not right:
            return 0.0
        return 1.0 if left == right else 0.0

    def score(self, resource: Resource, need: Need) -> int:
        weights = {
            "category": 40,
            "format": 25,
            "location": 20,
            "exchange": 15,
        }
        raw = 0.0
        max_weight = 0.0

        if resource.category and need.category:
            similarity = self._similarity(resource.category, need.category)
            raw += similarity * weights["category"]
            max_weight += weights["category"]
        if resource.resource_type and need.format_type:
            raw += self._match_format(resource.resource_type, need.format_type) * weights[
                "format"
            ]
            max_weight += weights["format"]
        if resource.location and need.location:
            raw += self._similarity(resource.location, need.location) * weights[
                "location"
            ]
            max_weight += weights["location"]
        if resource.exchange_type and need.exchange_type:
            raw += self._match_exchange(resource.exchange_type, need.exchange_type) * weights[
                "exchange"
            ]
            max_weight += weights["exchange"]

        if max_weight < 40:
            return 0
        return int((raw / max_weight) * 100)
