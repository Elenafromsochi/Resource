from __future__ import annotations

from models.user import User


def recalc_rating(user: User) -> float:
    # Simple heuristic for MVP
    balance_factor = user.gift_balance * 0.05
    exchange_factor = (user.gifts_given - user.gifts_received) * 0.1
    score = 4.5 + balance_factor + exchange_factor
    return max(0.0, min(5.0, score))


def apply_deal_completion(provider: User, receiver: User) -> None:
    provider.gifts_given += 1
    receiver.gifts_received += 1
    provider.gift_balance += 1
    receiver.gift_balance -= 1
    provider.rating_score = recalc_rating(provider)
    receiver.rating_score = recalc_rating(receiver)
