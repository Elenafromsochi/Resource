"""Человеческий договор — главный дифференциатор «Ресурса».

Договор собирается в реальном времени по ходу диалога в чате сделки.
Принцип: один акт = один договор. Встречная передача — отдельный документ.
Договор «живой»: меняется по обоюдному согласию (поля можно дополнять,
подписи сбрасываются при изменении после подписания).

Шаблон полей:
  essence          — суть: что и зачем передаётся
  value_exchange   — обмен ценностями: что сторона получает взамен (может быть пусто —
                     даю и прошу независимы, встречной ценности может не быть)
  quality_criteria — критерии качества: как поймём, что всё хорошо
  plan_b           — план Б: что делаем, если что-то пойдёт не так
  declaration      — декларация: общие договорённости и намерения сторон
"""

from __future__ import annotations

CONTRACT_FIELDS = [
    {"key": "essence", "label": "Суть"},
    {"key": "value_exchange", "label": "Обмен ценностями"},
    {"key": "quality_criteria", "label": "Критерии качества"},
    {"key": "plan_b", "label": "План Б"},
    {"key": "declaration", "label": "Декларация"},
]

CONTRACT_FIELD_KEYS = [f["key"] for f in CONTRACT_FIELDS]


def empty_contract() -> dict:
    """Пустой договор: все поля шаблона + пустые подписи."""
    return {
        "fields": {key: "" for key in CONTRACT_FIELD_KEYS},
        "signatures": {},  # user_id -> bool
    }


def apply_update(contract: dict, updates: dict, by_user_id: str | None = None) -> dict:
    """Дополнить/изменить поля договора.

    Любое изменение поля сбрасывает все подписи — договор снова требует согласия
    обеих сторон (живой документ, меняется по обоюдному согласию).
    """
    fields = dict(contract.get("fields", {}))
    changed = False
    for key, value in updates.items():
        if key not in CONTRACT_FIELD_KEYS:
            continue
        if fields.get(key, "") != value:
            fields[key] = value
            changed = True
    result = {
        "fields": fields,
        "signatures": {} if changed else dict(contract.get("signatures", {})),
    }
    return result


def sign(contract: dict, user_id: str) -> dict:
    """Поставить подпись стороны."""
    signatures = dict(contract.get("signatures", {}))
    signatures[str(user_id)] = True
    return {"fields": dict(contract.get("fields", {})), "signatures": signatures}


def completeness(contract: dict) -> float:
    """Доля заполненных полей шаблона (0..1). value_exchange не обязателен."""
    fields = contract.get("fields", {})
    required = [k for k in CONTRACT_FIELD_KEYS if k != "value_exchange"]
    filled = sum(1 for k in required if str(fields.get(k, "")).strip())
    return round(filled / len(required), 2)


def is_signed_by_all(contract: dict, party_ids: list[str]) -> bool:
    """Подписан ли договор всеми сторонами сделки."""
    signatures = contract.get("signatures", {})
    return all(signatures.get(str(pid)) for pid in party_ids) and len(party_ids) > 0
