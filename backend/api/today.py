"""The Today dashboard (Phase 3): the daily calorie target + reconciled macro targets.

Food logging (calories consumed / left) arrives in Phase 4; for now this exposes the targets
derived from the profile, the self-correcting weight (Phase 2), and macro preferences.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import date

from fastapi import APIRouter, HTTPException

from backend.api.deps import CurrentUser, SessionDep
from backend.api.diary import sum_consumed
from backend.calories import engine
from backend.macros import engine as macro_engine
from backend.persistence import repository
from backend.schemas import MacroResultOut, MyCaloriesOut, TodayOut
from backend.weight import trend as wtrend

router = APIRouter(tags=["today"])


@router.get("/today", response_model=TodayOut)
def today(session: SessionDep, user: CurrentUser) -> TodayOut:
    profile = repository.get_profile(session, user.id)
    if profile is None:
        raise HTTPException(status_code=404, detail="profile not set")

    points = [(w.date, w.weight_kg) for w in repository.list_weigh_ins(session, user.id)]
    weight_kg, source = wtrend.effective_weight(points, date.today(), profile.weight_kg)
    cal = engine.compute(
        gender=profile.gender,
        weight_kg=weight_kg,
        height_cm=profile.height_cm,
        age=profile.age,
        activity=profile.activity_level,
        goal=profile.goal,
    )

    prefs = repository.get_macro_target(session, user.id)
    protein_g_per_kg = (
        prefs.protein_g_per_kg if prefs else macro_engine.DEFAULT_PROTEIN_G_PER_KG
    )
    fat_g_per_kg = prefs.fat_g_per_kg if prefs else macro_engine.DEFAULT_FAT_G_PER_KG
    macros = macro_engine.compute_macros(
        cal.target, weight_kg, protein_g_per_kg, fat_g_per_kg
    )

    consumed = sum_consumed(repository.list_food_logs(session, user.id, date.today()))

    return TodayOut(
        date=date.today(),
        calories=MyCaloriesOut(
            **asdict(cal), weight_kg=weight_kg, weight_source=source.value
        ),
        macros=MacroResultOut.model_validate(macros),
        consumed=consumed,
        remaining_kcal=cal.target - consumed.kcal,
    )
