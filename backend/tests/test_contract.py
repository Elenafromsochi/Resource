"""Тесты Человеческого договора."""

from app.contract import (
    apply_update,
    completeness,
    empty_contract,
    is_signed_by_all,
    sign,
)


def test_empty_contract_has_all_fields():
    c = empty_contract()
    assert set(c["fields"]) == {
        "essence",
        "value_exchange",
        "quality_criteria",
        "plan_b",
        "declaration",
    }
    assert c["signatures"] == {}


def test_apply_update_fills_field():
    c = apply_update(empty_contract(), {"essence": "Помощь с переездом"})
    assert c["fields"]["essence"] == "Помощь с переездом"


def test_value_exchange_not_required_for_completeness():
    c = empty_contract()
    for key in ("essence", "quality_criteria", "plan_b", "declaration"):
        c = apply_update(c, {key: "x"})
    # value_exchange пустой, но договор полон — даю и прошу независимы.
    assert completeness(c) == 1.0


def test_editing_after_signing_resets_signatures():
    c = empty_contract()
    for key in ("essence", "quality_criteria", "plan_b", "declaration"):
        c = apply_update(c, {key: "x"})
    c = sign(c, "user-a")
    c = sign(c, "user-b")
    assert is_signed_by_all(c, ["user-a", "user-b"]) is True
    # Любая правица поля сбрасывает подписи — живой документ.
    c = apply_update(c, {"essence": "новая суть"}, "user-a")
    assert c["signatures"] == {}
    assert is_signed_by_all(c, ["user-a", "user-b"]) is False


def test_unchanged_update_keeps_signatures():
    c = apply_update(empty_contract(), {"essence": "та же"})
    c = sign(c, "user-a")
    c2 = apply_update(c, {"essence": "та же"}, "user-a")  # значение не изменилось
    assert c2["signatures"] == {"user-a": True}
