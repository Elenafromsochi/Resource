"""Сделка: чат с ботами + Человеческий договор + завершение + отзыв STAR.

Главный дифференциатор «Ресурса»: по ходу диалога в чате в реальном времени
собирается Человеческий договор. Один акт = один договор.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_profile
from ..contract import (
    CONTRACT_FIELDS,
    apply_update,
    completeness,
    empty_contract,
    is_signed_by_all,
    sign,
)
from ..db import get_db
from ..models import Act, Deal, Message, Need, Profile, Resource, Review
from ..reputation import recompute_trust
from ..schemas import ContractUpdateIn, DealCreateIn, MessageIn, ReviewIn

router = APIRouter(prefix="/deals", tags=["deals"])

# Сопоставление человеческих подписей/ключей полям договора (для разбора реплик).
_FIELD_LOOKUP = {f["label"].lower(): f["key"] for f in CONTRACT_FIELDS}
_FIELD_LOOKUP.update({f["key"]: f["key"] for f in CONTRACT_FIELDS})


def _parties(deal: Deal) -> list[str]:
    return [deal.giver_id, deal.taker_id]


def _next_empty_field(contract: dict) -> dict | None:
    fields = contract.get("fields", {})
    for f in CONTRACT_FIELDS:
        if f["key"] == "value_exchange":
            continue  # необязательное — даю и прошу независимы
        if not str(fields.get(f["key"], "")).strip():
            return f
    return None


def _bot_prompt(contract: dict) -> str:
    nxt = _next_empty_field(contract)
    if nxt is None:
        return "Договор заполнен. Осталось подписать его обеим сторонам."
    return (
        f"Давайте зафиксируем поле «{nxt['label']}». "
        f"Напишите в формате «{nxt['label']}: ваш текст»."
    )


def _add_message(db: Session, deal_id: str, role: str, text: str, sender_id: str | None = None) -> Message:
    msg = Message(deal_id=deal_id, role=role, text=text, sender_id=sender_id)
    db.add(msg)
    return msg


def _serialize(deal: Deal) -> dict:
    return {
        "id": deal.id,
        "status": deal.status,
        "giver_id": deal.giver_id,
        "taker_id": deal.taker_id,
        "resource_id": deal.resource_id,
        "need_id": deal.need_id,
        "contract": deal.contract,
        "contract_completeness": completeness(deal.contract or empty_contract()),
        "signed_by_all": is_signed_by_all(deal.contract or {}, _parties(deal)),
        "messages": [
            {"id": m.id, "role": m.role, "sender_id": m.sender_id, "text": m.text}
            for m in deal.messages
        ],
    }


def _load_party_deal(db: Session, deal_id: str, profile: Profile) -> Deal:
    deal = db.get(Deal, deal_id)
    if deal is None:
        raise HTTPException(status_code=404, detail="Сделка не найдена")
    if profile.id not in _parties(deal):
        raise HTTPException(status_code=403, detail="Вы не участник сделки")
    return deal


@router.post("")
def create_deal(
    body: DealCreateIn,
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> dict:
    if not body.resource_id and not body.need_id:
        raise HTTPException(status_code=422, detail="Нужен resource_id или need_id")

    if body.resource_id:
        resource = db.get(Resource, body.resource_id)
        if resource is None:
            raise HTTPException(status_code=404, detail="Ресурс не найден")
        giver_id, taker_id = resource.owner_id, body.counterparty_id
    else:
        need = db.get(Need, body.need_id)
        if need is None:
            raise HTTPException(status_code=404, detail="Потребность не найдена")
        taker_id, giver_id = need.owner_id, body.counterparty_id

    if giver_id == taker_id:
        raise HTTPException(status_code=422, detail="Стороны сделки совпадают")
    if profile.id not in (giver_id, taker_id):
        raise HTTPException(status_code=403, detail="Вы не участник сделки")

    deal = Deal(
        resource_id=body.resource_id,
        need_id=body.need_id,
        giver_id=giver_id,
        taker_id=taker_id,
        contract=empty_contract(),
    )
    db.add(deal)
    db.flush()
    _add_message(db, deal.id, "bot_resurs", "Открываю сделку. Я помогу собрать Человеческий договор.")
    _add_message(db, deal.id, "bot_mediator", "Я медиатор. Подключусь, если возникнут разногласия.")
    _add_message(db, deal.id, "bot_resurs", _bot_prompt(deal.contract))
    db.commit()
    db.refresh(deal)
    return _serialize(deal)


@router.get("/{deal_id}")
def get_deal(
    deal_id: str,
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> dict:
    return _serialize(_load_party_deal(db, deal_id, profile))


@router.post("/{deal_id}/messages")
def post_message(
    deal_id: str,
    body: MessageIn,
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> dict:
    deal = _load_party_deal(db, deal_id, profile)
    _add_message(db, deal.id, "user", body.text, sender_id=profile.id)

    # Реплика вида «Поле: значение» в реальном времени дополняет договор.
    if ":" in body.text:
        label, _, value = body.text.partition(":")
        key = _FIELD_LOOKUP.get(label.strip().lower())
        if key and value.strip():
            deal.contract = apply_update(deal.contract or empty_contract(), {key: value.strip()}, profile.id)
            _add_message(db, deal.id, "bot_resurs", f"Записал «{label.strip()}» в договор.")

    _add_message(db, deal.id, "bot_resurs", _bot_prompt(deal.contract or empty_contract()))
    db.commit()
    db.refresh(deal)
    return _serialize(deal)


@router.patch("/{deal_id}/contract")
def update_contract(
    deal_id: str,
    body: ContractUpdateIn,
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> dict:
    deal = _load_party_deal(db, deal_id, profile)
    deal.contract = apply_update(deal.contract or empty_contract(), body.updates, profile.id)
    deal.status = "open"  # правка договора сбрасывает подписи → снова открыт
    db.commit()
    db.refresh(deal)
    return _serialize(deal)


@router.post("/{deal_id}/sign")
def sign_contract(
    deal_id: str,
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> dict:
    deal = _load_party_deal(db, deal_id, profile)
    if _next_empty_field(deal.contract or empty_contract()) is not None:
        raise HTTPException(status_code=422, detail="Договор ещё не заполнен")
    deal.contract = sign(deal.contract, profile.id)
    if is_signed_by_all(deal.contract, _parties(deal)):
        deal.status = "signed"
        _add_message(db, deal.id, "bot_resurs", "Договор подписан обеими сторонами. Можно завершать сделку.")
    db.commit()
    db.refresh(deal)
    return _serialize(deal)


@router.post("/{deal_id}/complete")
def complete_deal(
    deal_id: str,
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> dict:
    deal = _load_party_deal(db, deal_id, profile)
    if deal.status != "signed":
        raise HTTPException(status_code=422, detail="Сначала подпишите договор обеими сторонами")
    act = Act(
        deal_id=deal.id,
        giver_id=deal.giver_id,
        taker_id=deal.taker_id,
        contract_snapshot=deal.contract,
    )
    db.add(act)
    deal.status = "completed"
    # STAR-черновик отзыва из подписанного договора.
    fields = (deal.contract or {}).get("fields", {})
    star_draft = {
        "situation": fields.get("essence", ""),
        "task": fields.get("quality_criteria", ""),
        "action": fields.get("declaration", ""),
        "result": fields.get("value_exchange", ""),
    }
    db.flush()
    _add_message(db, deal.id, "bot_resurs", "Сделка завершена. Подготовил черновик отзыва по STAR.")
    db.commit()
    db.refresh(act)
    return {"deal": _serialize(deal), "act_id": act.id, "star_draft": star_draft}


@router.post("/acts/{act_id}/review")
def leave_review(
    act_id: str,
    body: ReviewIn,
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> dict:
    act = db.get(Act, act_id)
    if act is None:
        raise HTTPException(status_code=404, detail="Акт не найден")
    if profile.id not in (act.giver_id, act.taker_id):
        raise HTTPException(status_code=403, detail="Вы не участник акта")
    subject_id = act.taker_id if profile.id == act.giver_id else act.giver_id
    # Коэффициент полноты отзыва: чем подробнее STAR, тем выше вес.
    filled = sum(1 for v in (body.situation, body.task, body.action, body.result) if v.strip())
    coefficient = round(0.7 + 0.1 * filled, 2)  # 0.7..1.1
    review = Review(
        act_id=act.id,
        author_id=profile.id,
        subject_id=subject_id,
        situation=body.situation,
        task=body.task,
        action=body.action,
        result=body.result,
        rating=max(1, min(5, body.rating)),
        coefficient=coefficient,
    )
    db.add(review)
    db.flush()
    new_trust = recompute_trust(db, subject_id)
    db.commit()
    return {"review_id": review.id, "subject_id": subject_id, "subject_trust_capital": new_trust}
