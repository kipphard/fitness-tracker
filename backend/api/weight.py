"""Weight tracking endpoints (Phase 2): daily weigh-ins + weekly average + EWMA trend."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Response

from backend.api.deps import CurrentUser, SessionDep
from backend.persistence import repository
from backend.schemas import (
    TrendPointOut,
    WeekAverageOut,
    WeighInIn,
    WeighInOut,
    WeightTrendOut,
)
from backend.weight import trend as wtrend

router = APIRouter(prefix="/weight", tags=["weight"])


@router.put("", response_model=WeighInOut)
def log_weight(payload: WeighInIn, session: SessionDep, user: CurrentUser) -> WeighInOut:
    """Log (or overwrite) the weigh-in for a day. Defaults to today."""
    day = payload.date or date.today()
    weigh_in = repository.upsert_weigh_in(session, user.id, day, payload.weight_kg)
    session.commit()
    return WeighInOut.model_validate(weigh_in)


@router.get("", response_model=list[WeighInOut])
def list_weight(session: SessionDep, user: CurrentUser) -> list[WeighInOut]:
    rows = repository.list_weigh_ins(session, user.id)
    return [WeighInOut.model_validate(w) for w in rows]


@router.get("/trend", response_model=WeightTrendOut)
def weight_trend(session: SessionDep, user: CurrentUser) -> WeightTrendOut:
    rows = repository.list_weigh_ins(session, user.id)
    points = [(w.date, w.weight_kg) for w in rows]
    ewma = wtrend.ewma_trend(points)
    weekly = wtrend.weekly_averages(points)

    effective_weight = None
    effective_source = None
    if points:
        profile = repository.get_profile(session, user.id)
        fallback = profile.weight_kg if profile is not None else points[-1][1]
        ew, source = wtrend.effective_weight(points, date.today(), fallback)
        effective_weight, effective_source = ew, source.value

    return WeightTrendOut(
        points=[WeighInOut.model_validate(w) for w in rows],
        ewma=[TrendPointOut(date=p.date, trend=p.trend) for p in ewma],
        weekly=[
            WeekAverageOut(week_start=w.week_start, average=w.average, count=w.count)
            for w in weekly
        ],
        current_trend=ewma[-1].trend if ewma else None,
        effective_weight=effective_weight,
        effective_source=effective_source,
    )


@router.delete("/{day}", status_code=204)
def delete_weight(day: date, session: SessionDep, user: CurrentUser) -> Response:
    repository.delete_weigh_in(session, user.id, day)
    session.commit()
    return Response(status_code=204)
