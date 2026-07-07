"""The Today dashboard (Phase 3): the daily calorie target + reconciled macro targets.

Food logging (calories consumed / left) arrives in Phase 4; for now this exposes the targets
derived from the profile, the self-correcting weight (Phase 2), and macro preferences.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.deps import CurrentUser, SessionDep
from backend.api.diary import sum_consumed
from backend.calories import adaptive, engine
from backend.config import get_settings as get_app_settings
from backend.macros import engine as macro_engine
from backend.persistence import repository
from backend.persistence.models import User
from backend.schemas import MacroResultOut, MyCaloriesOut, TodayOut
from backend.steps.convert import steps_to_kcal
from backend.weight import trend as wtrend
from backend.workouts.calories import session_kcal

router = APIRouter(tags=["today"])


def activity_by_day(
    session: Session,
    user: User,
    points: list[tuple[date, Decimal]],
    fallback_weight: Decimal,
    start_day: date,
    end_day: date,
    tz: int = 0,
) -> dict[date, Decimal]:
    """Per-day deliberate-exercise kcal (steps + workouts) over ``[start_day, end_day)``.

    Fed to the adaptive-TDEE correction so the measured maintenance excludes exercise (see
    ``backend.calories.adaptive``). Reuses the same per-day math as ``compute_today``: steps via
    ``steps_to_kcal`` and workouts via ``session_kcal``, each priced at that day's effective
    weight and bucketed to the session's local calendar day using ``tz``.
    """
    steps_by_day: dict[date, int] = {
        sl.date: sl.steps
        for sl in repository.list_step_logs(session, user.id)
        if start_day <= sl.date < end_day
    }

    # Query a day wider on each side (UTC) then filter by local day, so tz can't drop edge sessions.
    win_start = datetime(start_day.year, start_day.month, start_day.day, tzinfo=timezone.utc)
    win_end = datetime(end_day.year, end_day.month, end_day.day, tzinfo=timezone.utc)
    workout_by_day: dict[date, Decimal] = {}
    for s in repository.list_workout_sessions_between(
        session, user.id, win_start - timedelta(days=1), win_end + timedelta(days=1)
    ):
        local_day = (s.started_at + timedelta(minutes=tz)).date()
        if not (start_day <= local_day < end_day):
            continue
        weight, _ = wtrend.effective_weight(points, local_day, fallback_weight)
        workout_by_day[local_day] = workout_by_day.get(local_day, Decimal(0)) + session_kcal(
            weight, started_at=s.started_at, ended_at=s.ended_at, set_count=len(s.sets)
        )

    out: dict[date, Decimal] = {}
    for d in set(steps_by_day) | set(workout_by_day):
        weight, _ = wtrend.effective_weight(points, d, fallback_weight)
        out[d] = steps_to_kcal(steps_by_day.get(d, 0), weight) + workout_by_day.get(d, Decimal(0))
    return out


@router.get("/today", response_model=TodayOut)
def today(
    session: SessionDep,
    user: CurrentUser,
    on: date | None = Query(default=None, alias="date"),
    tz: int = Query(default=0, alias="tz", description="minutes east of UTC (e.g. Berlin DST = 120)"),
) -> TodayOut:
    return compute_today(session, user, on or date.today(), tz)


def compute_today(session: Session, user: User, day: date, tz: int = 0) -> TodayOut:
    """The Today snapshot for ``day`` — targets, consumed, remaining, activity, net deficit.

    Extracted from the route so other endpoints (e.g. "fill remaining calories" suggestions)
    reuse the exact same remaining-kcal and macro math. Raises 404 if the profile isn't set.
    """
    profile = repository.get_profile(session, user.id)
    if profile is None:
        raise HTTPException(status_code=404, detail="profile not set")

    points = [(w.date, w.weight_kg) for w in repository.list_weigh_ins(session, user.id)]
    weight_kg, source = wtrend.effective_weight(points, day, profile.weight_kg)
    cal = engine.compute(
        gender=profile.gender,
        weight_kg=weight_kg,
        height_cm=profile.height_cm,
        age=profile.age,
        activity=profile.activity_level,
        goal=profile.goal,
    )

    # Adaptive TDEE (#4): correct the formula maintenance toward the value measured from intake
    # vs. weight change, once enough recent data exists. Everything downstream (target, net
    # deficit, weekly-loss prediction) then uses this self-correcting maintenance. Activity over
    # the window is passed in so `measured` excludes exercise (added back on top once, below).
    window_start = day - timedelta(days=adaptive.WINDOW_DAYS)
    adapt = adaptive.adaptive_maintenance(
        formula=cal.maintenance,
        weigh_points=points,
        intake_by_day=repository.daily_intake(session, user.id, window_start, day),
        today=day,
        activity_by_day=activity_by_day(
            session, user, points, profile.weight_kg, window_start, day, tz
        ),
    )
    maintenance = adapt.maintenance
    target = engine.goal_target(maintenance, profile.gender, profile.goal)
    below_floor = (maintenance + engine.GOAL_ADJUSTMENT[profile.goal]) < cal.floor

    prefs = repository.get_macro_target(session, user.id)
    protein_g_per_kg = (
        prefs.protein_g_per_kg if prefs else macro_engine.DEFAULT_PROTEIN_G_PER_KG
    )
    fat_g_per_kg = prefs.fat_g_per_kg if prefs else macro_engine.DEFAULT_FAT_G_PER_KG
    macros = macro_engine.compute_macros(
        target, weight_kg, protein_g_per_kg, fat_g_per_kg
    )

    consumed = sum_consumed(repository.list_food_logs(session, user.id, day))

    step_log = repository.get_step_log(session, user.id, day)
    steps = step_log.steps if step_log else 0

    # Workout burn: sessions whose local calendar day is `day`. `tz` (minutes east of UTC)
    # turns the local day into a UTC window so a session is counted on the day it happened.
    local_midnight = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    start_utc = local_midnight - timedelta(minutes=tz)
    sessions = repository.list_workout_sessions_between(
        session, user.id, start_utc, start_utc + timedelta(days=1)
    )
    workout_kcal = sum(
        (
            session_kcal(
                weight_kg,
                started_at=s.started_at,
                ended_at=s.ended_at,
                set_count=len(s.sets),
            )
            for s in sessions
        ),
        Decimal(0),
    )

    # activity_kcal = steps + workouts → flows into net deficit and (with eat-back) the budget.
    activity_kcal = steps_to_kcal(steps, weight_kg) + workout_kcal

    prefs = repository.get_settings(session, user.id)
    eat_back = bool(prefs.eat_back_activity) if prefs else False
    budget = target + (activity_kcal if eat_back else Decimal(0))

    cal_data = asdict(cal)
    cal_data.update(maintenance=maintenance, target=target, below_floor=below_floor)

    return TodayOut(
        date=day,
        calories=MyCaloriesOut(
            **cal_data,
            weight_kg=weight_kg,
            weight_source=source.value,
            formula_maintenance=adapt.formula,
            measured_maintenance=adapt.measured,
            tdee_confidence=adapt.confidence,
        ),
        macros=MacroResultOut.model_validate(macros),
        consumed=consumed,
        remaining_kcal=budget - consumed.kcal,
        steps=steps,
        activity_kcal=activity_kcal,
        workout_kcal=workout_kcal,
        net_deficit_kcal=(maintenance + activity_kcal) - consumed.kcal,
        eat_back_activity=eat_back,
        ai_available=get_app_settings().anthropic_configured,
    )
