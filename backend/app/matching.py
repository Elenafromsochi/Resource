"""Зеркальный мэтчинг ресурса (Даю) и потребности (Прошу).

Алгоритм (из брифа):
  1. Жёсткая фильтрация: категория, гео, сроки, совместимость условий передачи.
     Если хоть один жёсткий критерий не сошёлся — пары нет (балл = None).
  2. Балл соответствия 0..100 по весам параметров (важные параметры — вес x4).
  3. Корректировка репутацией дающего (капитал доверия 0..100).
  4. Порог мэтча — настраиваемый, по умолчанию 40%.

Функции чистые: работают с обычными dict, без БД, чтобы их было легко тестировать.
Ресурс и потребность представлены как:
    {"category": str, "location": str, "fields": {<key>: <value>, ...}}
где transfer_terms — список допустимых способов передачи.
"""

from __future__ import annotations

from .categories import ORDINAL_SCALES, fields_for

DEFAULT_THRESHOLD = 40.0
REMOTE_MARKERS = {"remote", "удалённо", "удаленно", "online", "онлайн", "любой", "any"}


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _location_compatible(resource_loc, need_loc) -> bool:
    """Гео совместимо, если совпадает, либо одна из сторон допускает удалёнку/любое место."""
    r = (resource_loc or "").strip().lower()
    n = (need_loc or "").strip().lower()
    if not r or not n:
        return True  # локация не указана — не блокируем
    if r in REMOTE_MARKERS or n in REMOTE_MARKERS:
        return True
    return r == n


def _terms_compatible(resource_terms, need_terms) -> bool:
    """Условия совместимы, если есть хотя бы один общий способ передачи."""
    r = set(_as_list(resource_terms))
    n = set(_as_list(need_terms))
    if not r or not n:
        return True
    return bool(r & n)


def _ordinal_score(key, resource_value, need_value) -> float:
    """Дающий должен предлагать уровень не ниже запрошенного. Чем выше — тем лучше."""
    scale = ORDINAL_SCALES.get(key)
    if scale is None:
        return 1.0 if resource_value == need_value else 0.0
    try:
        r_idx = scale.index(resource_value)
        n_idx = scale.index(need_value)
    except ValueError:
        return 0.0
    if r_idx >= n_idx:
        return 1.0
    # Ниже запрошенного — частичный балл, падает с дистанцией.
    gap = n_idx - r_idx
    return max(0.0, 1.0 - gap / len(scale))


def _overlap_score(resource_value, need_value) -> float:
    """Доля запрошенного, что покрыта предложением (пересечение множеств)."""
    r = set(_as_list(resource_value))
    n = set(_as_list(need_value))
    if not n:
        return 1.0
    if not r:
        return 0.0
    return len(r & n) / len(n)


def _field_score(spec, resource_value, need_value) -> float:
    """Балл 0..1 по одному параметру согласно его типу сравнения."""
    if need_value in (None, "", [], {}):
        return 1.0  # сторона "Прошу" не задала требование — параметр не ограничивает
    kind = spec["match"]
    if kind == "equals":
        return 1.0 if resource_value == need_value else 0.0
    if kind == "gte":
        return _ordinal_score(spec["key"], resource_value, need_value)
    if kind in ("overlap", "terms"):
        return _overlap_score(resource_value, need_value)
    if kind == "location":
        return 1.0 if _location_compatible(resource_value, need_value) else 0.0
    return 0.0


def passes_hard_filters(resource: dict, need: dict) -> bool:
    """Шаг 1: жёсткие фильтры. True — пара допустима к расчёту балла."""
    if resource.get("category") != need.get("category"):
        return False
    if not _location_compatible(resource.get("location"), need.get("location")):
        return False
    r_fields = resource.get("fields", {})
    n_fields = need.get("fields", {})
    if not _terms_compatible(r_fields.get("transfer_terms"), n_fields.get("transfer_terms")):
        return False
    return True


def base_score(resource: dict, need: dict) -> float:
    """Шаг 2: взвешенный балл 0..100 по параметрам категории."""
    category = resource.get("category")
    r_fields = resource.get("fields", {})
    n_fields = need.get("fields", {})
    total_weight = 0.0
    acc = 0.0
    for spec in fields_for(category):
        weight = spec["weight"]
        total_weight += weight
        acc += weight * _field_score(spec, r_fields.get(spec["key"]), n_fields.get(spec["key"]))
    if total_weight == 0:
        return 0.0
    return round(100.0 * acc / total_weight, 1)


def reputation_adjust(score: float, trust_capital: float) -> float:
    """Шаг 3: коррекция репутацией дающего.

    Капитал доверия 0..100 даёт множитель в диапазоне [0.9 .. 1.1]:
    нейтральная репутация (50) ничего не меняет, высокая немного поднимает,
    низкая немного опускает. Балл остаётся в пределах 0..100.
    """
    trust = max(0.0, min(100.0, trust_capital))
    multiplier = 0.9 + 0.2 * (trust / 100.0)
    return round(max(0.0, min(100.0, score * multiplier)), 1)


def match_score(resource: dict, need: dict, giver_trust: float = 50.0) -> float | None:
    """Полный конвейер. Возвращает скорректированный балл 0..100 либо None.

    None означает, что пара отсеяна жёсткими фильтрами (категория/гео/условия).
    """
    if not passes_hard_filters(resource, need):
        return None
    return reputation_adjust(base_score(resource, need), giver_trust)


def is_match(score: float | None, threshold: float = DEFAULT_THRESHOLD) -> bool:
    """Шаг 4: проверка порога."""
    return score is not None and score >= threshold
