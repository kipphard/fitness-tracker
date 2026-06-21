"""Trends + the weekly rate-of-loss guardrail (Phase 8)."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter

from backend.api.deps import CurrentUser, SessionDep
from backend.api.diary import sum_consumed
from backend.calories import engine
from backend.persistence import repository
from backend.schemas import AdherenceDayOut, TrendsOut, WeeklyWeightOut
from backend.weight import trend as wtrend

router = APIRouter(tags=["trends"])

_ADHERENCE_DAYS = 14
# Losing more than ~1% of bodyweight per week risks muscle loss — flag it (master plan §13).
_MAX_WEEKLY_LOSS_PCT = Decimal("1.0")


@router.get("/trends", response_model=TrendsOut)
def trends(session: SessionDep, user: CurrentUser) -> TrendsOut:
    today = date.today()
    profile = repository.get_profile(session, user.id)
    weigh_points = [
        (w.date, w.weight_kg) for w in repository.list_weigh_ins(session, user.id)
    ]

    target = None
    if profile is not None:
        weight, _ = wtrend.effective_weight(weigh_points, today, profile.weight_kg)
        target = engine.compute(
            gender=profile.gender,
            weight_kg=weight,
            height_cm=profile.height_cm,
            age=profile.age,
            activity=profile.activity_level,
            goal=profile.goal,
        ).target

    adherence: list[AdherenceDayOut] = []
    for offset in range(_ADHERENCE_DAYS - 1, -1, -1):
        day = today - timedelta(days=offset)
        consumed = sum_consumed(repository.list_food_logs(session, user.id, day)).kcal
        adherence.append(
            AdherenceDayOut(date=day, consumed=consumed, target=target or Decimal(0))
        )

    weekly_weight = [
        WeeklyWeightOut(week_start=w.week_start, average=w.average)
        for w in wtrend.weekly_averages(weigh_points)
    ]

    change = wtrend.weekly_change(weigh_points, today)
    rate_warning = False
    if change is not None and change < 0:
        current = wtrend.latest_weight(weigh_points) or (
            profile.weight_kg if profile else None
        )
        if current and current > 0:
            rate_warning = (-change / current) * 100 > _MAX_WEEKLY_LOSS_PCT

    return TrendsOut(
        target_kcal=target,
        adherence=adherence,
        weekly_weight=weekly_weight,
        weekly_change_kg=change,
        rate_warning=rate_warning,
    )
