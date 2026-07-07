"""Trends + the weekly rate-of-loss guardrail (Phase 8)."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter

from backend.api.deps import CurrentUser, SessionDep
from backend.api.diary import sum_consumed
from backend.api.today import activity_by_day
from backend.calories import adaptive, engine
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
    adapt: adaptive.AdaptiveResult | None = None
    if profile is not None:
        weight, _ = wtrend.effective_weight(weigh_points, today, profile.weight_kg)
        cal = engine.compute(
            gender=profile.gender,
            weight_kg=weight,
            height_cm=profile.height_cm,
            age=profile.age,
            activity=profile.activity_level,
            goal=profile.goal,
        )
        # Adaptive TDEE (#4): same self-correcting maintenance the Today target uses (measured
        # excludes exercise via the window's activity; tz=0 here — only workout day-bucketing is
        # tz-sensitive and it's a window average, so the effect is negligible).
        window_start = today - timedelta(days=adaptive.WINDOW_DAYS)
        adapt = adaptive.adaptive_maintenance(
            formula=cal.maintenance,
            weigh_points=weigh_points,
            intake_by_day=repository.daily_intake(session, user.id, window_start, today),
            today=today,
            activity_by_day=activity_by_day(
                session, user, weigh_points, profile.weight_kg, window_start, today
            ),
        )
        target = engine.goal_target(adapt.maintenance, profile.gender, profile.goal)

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
        formula_maintenance=adapt.formula if adapt else None,
        measured_maintenance=adapt.measured if adapt else None,
        tdee_confidence=adapt.confidence if adapt else Decimal(0),
        tdee_days=adapt.span_days if adapt else 0,
    )
