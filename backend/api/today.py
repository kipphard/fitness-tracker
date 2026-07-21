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
from backend.calories import engine
from backend.config import get_settings as get_app_settings
from backend.macros import engine as macro_engine
from backend.persistence import repository
from backend.persistence.models import User
from backend.schemas import MacroResultOut, MyCaloriesOut, TodayOut
from backend.steps.convert import steps_to_kcal
from backend.weight import trend as wtrend
from backend.workouts.calories import session_kcal

router = APIRouter(tags=["today"])


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

    # Maintenance comes straight from the formula (profile stats × the weekly-average weight
    # above) — no adaptive correction from tracked intake, so untracked days can't skew it.
    maintenance = cal.maintenance
    target = cal.target

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

    return TodayOut(
        date=day,
        calories=MyCaloriesOut(
            **asdict(cal),
            weight_kg=weight_kg,
            weight_source=source.value,
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
