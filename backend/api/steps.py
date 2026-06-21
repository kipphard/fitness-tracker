"""Step logging endpoints (Phase 6).

A generic ingestion point: manual entry now, any source (Health Connect / HealthKit export,
a companion app) later. Calories are derived from the effective weight on read.
"""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Query

from backend.api.deps import CurrentUser, SessionDep
from backend.persistence import repository
from backend.schemas import StepsIn, StepsOut
from backend.steps.convert import steps_to_kcal
from backend.weight import trend as wtrend

router = APIRouter(prefix="/steps", tags=["steps"])


def _kcal_for(session: SessionDep, user_id: uuid.UUID, steps: int) -> Decimal:
    profile = repository.get_profile(session, user_id)
    if profile is None:
        return Decimal(0)
    points = [(w.date, w.weight_kg) for w in repository.list_weigh_ins(session, user_id)]
    weight, _ = wtrend.effective_weight(points, date.today(), profile.weight_kg)
    return steps_to_kcal(steps, weight)


@router.put("", response_model=StepsOut)
def log_steps(payload: StepsIn, session: SessionDep, user: CurrentUser) -> StepsOut:
    day = payload.date or date.today()
    log = repository.upsert_step_log(session, user.id, day, payload.steps)
    session.commit()
    return StepsOut(
        date=log.date, steps=log.steps, kcal=_kcal_for(session, user.id, log.steps)
    )


@router.get("", response_model=StepsOut)
def get_steps(
    session: SessionDep,
    user: CurrentUser,
    on: date | None = Query(default=None, alias="date"),
) -> StepsOut:
    day = on or date.today()
    log = repository.get_step_log(session, user.id, day)
    steps = log.steps if log else 0
    return StepsOut(date=day, steps=steps, kcal=_kcal_for(session, user.id, steps))
