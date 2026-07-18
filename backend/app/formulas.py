"""Формулы расчёта совпадений (КОД, не модель).

Стабильные, воспроизводимые вычисления для поиска подходящих пар.
"""

from __future__ import annotations

from typing import TypedDict


class IntakeState(TypedDict, total=False):
    """Состояние после extract_intake."""
    mode: str | None
    category: str | None
    object_text: str | None
    object_level: int | None
    transfer_form: str | None
    when_type: str | None
    when_window: str | None
    urgency: str | None
    where_mode: str | None
    where_geo: str | None
    where_side: str | None
    counter_value: list[str] | None
    priority_fields: list[str] | None
    evidence: dict


def calculate_match_score(resource: IntakeState, need: IntakeState) -> float:
    """Вычисляет оценку совпадения между ресурсом и потребностью (0.0 — 1.0).

    Args:
        resource: состояние с mode="resource"
        need: состояние с mode="need"

    Returns:
        Оценка от 0.0 (нет совпадения) до 1.0 (идеальное совпадение)
    """
    score = 0.0
    max_score = 0.0

    # Категория должна совпадать
    max_score += 1.0
    if resource.get("category") and need.get("category"):
        if resource["category"] == need["category"]:
            score += 1.0

    # Уровень: проверяем, что предлагаемый уровень >= требуемому
    max_score += 0.8
    res_level = resource.get("object_level")
    need_level = need.get("object_level")
    if res_level is not None and need_level is not None:
        if res_level >= need_level:
            score += 0.8
        else:
            # Близкий уровень даёт половину балла
            if abs(res_level - need_level) <= 1:
                score += 0.4

    # Форма передачи (для thing/space)
    max_score += 0.6
    res_transfer = resource.get("transfer_form")
    need_transfer = need.get("transfer_form")
    if res_transfer and need_transfer:
        if res_transfer == need_transfer:
            score += 0.6
    elif not res_transfer or not need_transfer:
        # Если одно из них не заполнено, игнорируем
        max_score -= 0.6

    # Регулярность (when_type)
    max_score += 0.5
    res_when = resource.get("when_type")
    need_when = need.get("when_type")
    if res_when and need_when:
        if res_when == need_when:
            score += 0.5
        elif (res_when == "regular" and need_when in ["period", "regular"]) or \
             (res_when in ["period", "regular"] and need_when == "regular"):
            score += 0.3

    # Место (where_mode)
    max_score += 0.7
    res_mode = resource.get("where_mode")
    need_mode = need.get("where_mode")
    if res_mode == "online" or need_mode == "online":
        # Онлайн совместимо с любым
        score += 0.7
    elif res_mode == "offline" and need_mode == "offline":
        # Оба офлайн — проверяем геолокацию
        score += 0.5

    # Геолокация (если оба офлайн)
    max_score += 0.5
    if res_mode == "offline" and need_mode == "offline":
        res_geo = resource.get("where_geo")
        need_geo = need.get("where_geo")
        if res_geo and need_geo:
            # Простая проверка: совпадает ли город/район
            if res_geo.lower() == need_geo.lower():
                score += 0.5
            elif _same_city(res_geo, need_geo):
                score += 0.3

    # Условия (counter_value)
    max_score += 0.8
    res_counter = resource.get("counter_value")
    need_counter = need.get("counter_value")
    if res_counter and need_counter:
        if any(c in res_counter for c in need_counter):
            score += 0.8
        elif "gift" in res_counter or "gift" in need_counter:
            # Дар совместим со всем
            score += 0.4
        elif "barter" in res_counter and "barter" in need_counter:
            score += 0.8

    if max_score == 0:
        return 0.0

    return round(score / max_score, 2)


def _same_city(geo1: str, geo2: str) -> bool:
    """Проверяет, в одном ли городе две геолокации."""
    cities = ["москв", "мск"]
    for city in cities:
        if city in geo1.lower() and city in geo2.lower():
            return True
    return False


def match_pair(resources: list[IntakeState], needs: list[IntakeState]) -> list[dict]:
    """Находит лучшие пары между ресурсами и потребностями.

    Args:
        resources: список состояний с mode="resource"
        needs: список состояний с mode="need"

    Returns:
        Отсортированный список пар: [{"resource": idx, "need": idx, "score": 0.85}, ...]
    """
    pairs = []

    for r_idx, resource in enumerate(resources):
        for n_idx, need in enumerate(needs):
            score = calculate_match_score(resource, need)
            if score > 0.5:  # Порог: минимум 50% совпадения
                pairs.append({
                    "resource_idx": r_idx,
                    "need_idx": n_idx,
                    "score": score,
                })

    # Сортируем по оценке (лучшие первыми)
    return sorted(pairs, key=lambda p: p["score"], reverse=True)
