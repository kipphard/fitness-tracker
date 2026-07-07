"""Food diary endpoints (Phase 4): log entries by date + meal slot, recent, copy-day."""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query, Response

from backend.api.deps import CurrentUser, SessionDep
from backend.food.scale import scale_per100
from backend.food.slots import allowed_slot_keys
from backend.persistence import repository
from backend.persistence.models import Food, FoodSource
from backend.schemas import (
    ConsumedOut,
    DiaryCopyIn,
    DiaryDayOut,
    DiaryEntryOut,
    DiaryIn,
    DiaryUpdateIn,
    FoodOut,
)

router = APIRouter(prefix="/diary", tags=["diary"])


def sum_consumed(logs) -> ConsumedOut:
    return ConsumedOut(
        kcal=sum((log.kcal for log in logs), Decimal(0)),
        protein_g=sum((log.protein_g for log in logs), Decimal(0)),
        fat_g=sum((log.fat_g for log in logs), Decimal(0)),
        carbs_g=sum((log.carbs_g for log in logs), Decimal(0)),
    )


def _day(session: SessionDep, user_id, day: date) -> DiaryDayOut:
    logs = repository.list_food_logs(session, user_id, day)
    return DiaryDayOut(
        date=day,
        entries=[DiaryEntryOut.model_validate(log) for log in logs],
        totals=sum_consumed(logs),
    )


def _validate_slot(session: SessionDep, user_id, slot: str) -> None:
    """Reject a slot the user hasn't defined (built-in or one of their custom slots)."""
    settings = repository.get_settings(session, user_id)
    if slot not in allowed_slot_keys(settings.meal_slots if settings else None):
        raise HTTPException(status_code=422, detail="unknown meal slot")


def _resolve_food(session: SessionDep, user_id, payload: DiaryIn) -> Food:
    if payload.food_id is not None:
        food = repository.get_food(session, payload.food_id, user_id)
        if food is None:
            raise HTTPException(status_code=404, detail="food not found")
        return food
    if payload.food is not None:
        return repository.create_food(
            session,
            user_id,
            source=FoodSource.custom,
            name=payload.food.name,
            barcode=payload.food.barcode,
            per100_kcal=payload.food.per100_kcal,
            per100_protein_g=payload.food.per100_protein_g,
            per100_fat_g=payload.food.per100_fat_g,
            per100_carbs_g=payload.food.per100_carbs_g,
            serving_g=payload.food.serving_g,
        )
    raise HTTPException(status_code=400, detail="food_id or food is required")


@router.post("", response_model=DiaryEntryOut, status_code=201)
def add_entry(payload: DiaryIn, session: SessionDep, user: CurrentUser) -> DiaryEntryOut:
    _validate_slot(session, user.id, payload.slot)
    food = _resolve_food(session, user.id, payload)
    scaled = scale_per100(
        per100_kcal=food.per100_kcal,
        per100_protein_g=food.per100_protein_g,
        per100_fat_g=food.per100_fat_g,
        per100_carbs_g=food.per100_carbs_g,
        amount_g=payload.amount_g,
    )
    log = repository.create_food_log(
        session,
        user.id,
        date=payload.date or date.today(),
        slot=payload.slot,
        food_id=food.id,
        food_name=food.name,
        amount_g=payload.amount_g,
        kcal=scaled.kcal,
        protein_g=scaled.protein_g,
        fat_g=scaled.fat_g,
        carbs_g=scaled.carbs_g,
    )
    session.commit()
    return DiaryEntryOut.model_validate(log)


@router.get("", response_model=DiaryDayOut)
def get_day(
    session: SessionDep,
    user: CurrentUser,
    on: date | None = Query(default=None, alias="date"),
) -> DiaryDayOut:
    return _day(session, user.id, on or date.today())


@router.get("/recent", response_model=list[FoodOut])
def recent(session: SessionDep, user: CurrentUser) -> list[FoodOut]:
    return [FoodOut.model_validate(f) for f in repository.recent_foods(session, user.id)]


@router.post("/copy", response_model=DiaryDayOut)
def copy_day(
    payload: DiaryCopyIn, session: SessionDep, user: CurrentUser
) -> DiaryDayOut:
    to_day = payload.to_date or date.today()
    for log in repository.list_food_logs(session, user.id, payload.from_date):
        repository.create_food_log(
            session,
            user.id,
            date=to_day,
            slot=log.slot,
            food_id=log.food_id,
            food_name=log.food_name,
            amount_g=log.amount_g,
            kcal=log.kcal,
            protein_g=log.protein_g,
            fat_g=log.fat_g,
            carbs_g=log.carbs_g,
        )
    session.commit()
    return _day(session, user.id, to_day)


@router.patch("/{log_id}", response_model=DiaryEntryOut)
def update_entry(
    log_id: uuid.UUID, payload: DiaryUpdateIn, session: SessionDep, user: CurrentUser
) -> DiaryEntryOut:
    log = repository.get_food_log(session, log_id, user.id)
    if log is None:
        raise HTTPException(status_code=404, detail="entry not found")
    if payload.slot is not None:
        _validate_slot(session, user.id, payload.slot)
        log.slot = payload.slot
    if payload.amount_g is not None:
        food = repository.get_food(session, log.food_id, user.id) if log.food_id else None
        if food is not None:
            scaled = scale_per100(
                per100_kcal=food.per100_kcal,
                per100_protein_g=food.per100_protein_g,
                per100_fat_g=food.per100_fat_g,
                per100_carbs_g=food.per100_carbs_g,
                amount_g=payload.amount_g,
            )
            log.kcal, log.protein_g = scaled.kcal, scaled.protein_g
            log.fat_g, log.carbs_g = scaled.fat_g, scaled.carbs_g
        else:
            ratio = payload.amount_g / log.amount_g
            log.kcal *= ratio
            log.protein_g *= ratio
            log.fat_g *= ratio
            log.carbs_g *= ratio
        log.amount_g = payload.amount_g
    session.commit()
    return DiaryEntryOut.model_validate(log)


@router.delete("/{log_id}", status_code=204)
def delete_entry(log_id: uuid.UUID, session: SessionDep, user: CurrentUser) -> Response:
    repository.delete_food_log(session, log_id, user.id)
    session.commit()
    return Response(status_code=204)
