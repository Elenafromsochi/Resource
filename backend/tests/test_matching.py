"""Тесты зеркального мэтчинга."""

from app.matching import (
    DEFAULT_THRESHOLD,
    base_score,
    is_match,
    match_score,
    passes_hard_filters,
    reputation_adjust,
)


def _resource(**fields):
    return {"category": "time_skill", "location": "Москва", "fields": fields}


def _need(**fields):
    return {"category": "time_skill", "location": "Москва", "fields": fields}


def test_hard_filter_blocks_different_category():
    res = {"category": "thing", "location": "Москва", "fields": {}}
    need = {"category": "knowledge", "location": "Москва", "fields": {}}
    assert passes_hard_filters(res, need) is False
    assert match_score(res, need) is None


def test_hard_filter_blocks_incompatible_terms():
    res = _resource(transfer_terms=["money"])
    need = _need(transfer_terms=["gift"])
    assert passes_hard_filters(res, need) is False


def test_remote_location_is_compatible():
    res = {"category": "time_skill", "location": "Москва", "fields": {}}
    need = {"category": "time_skill", "location": "remote", "fields": {}}
    assert passes_hard_filters(res, need) is True


def test_perfect_match_scores_100():
    res = _resource(
        qualification="expert",
        volume="10",
        availability=["будни"],
        transfer_terms=["gift"],
        location="Москва",
    )
    need = _need(
        qualification="expert",
        volume="10",
        availability=["будни"],
        transfer_terms=["gift"],
        location="Москва",
    )
    assert base_score(res, need) == 100.0


def test_important_fields_weigh_more():
    # Несовпадение важного поля (availability, вес x4) бьёт сильнее, чем
    # несовпадение обычного (volume, вес x1).
    res = _resource(qualification="expert", availability=["будни"], transfer_terms=["gift"])
    need_miss_important = _need(
        qualification="expert", availability=["выходные"], transfer_terms=["gift"]
    )
    need_miss_normal = _need(
        qualification="expert", availability=["будни"], transfer_terms=["gift"], volume="5"
    )
    # res без volume → обычное поле не покрыто (вес 1); важное availability покрыто.
    assert base_score(res, need_miss_normal) > base_score(res, need_miss_important)


def test_qualification_below_request_partial():
    res = _resource(qualification="novice", transfer_terms=["gift"])
    need = _need(qualification="expert", transfer_terms=["gift"])
    # Квалификация ниже запрошенной — частичный, не нулевой и не полный балл.
    assert 0 < base_score(res, need) < 100


def test_reputation_adjustment_bounds():
    assert reputation_adjust(80.0, 50.0) == 80.0  # нейтральная репутация не меняет
    assert reputation_adjust(80.0, 100.0) > 80.0  # высокая поднимает
    assert reputation_adjust(80.0, 0.0) < 80.0  # низкая опускает
    assert reputation_adjust(100.0, 100.0) <= 100.0  # не выходит за 100


def test_threshold_logic():
    assert is_match(40.0, DEFAULT_THRESHOLD) is True
    assert is_match(39.9, DEFAULT_THRESHOLD) is False
    assert is_match(None) is False
