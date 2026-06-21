"""Calorie engine endpoints (Phase 1)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.api.deps import CurrentUser, SessionDep
from backend.calories import engine
from backend.persistence import repository
from backend.schemas import ActivityLevelOut, CalorieInput, CalorieResultOut

router = APIRouter(prefix="/calories", tags=["calories"])


@router.post("/calculate", response_model=CalorieResultOut)
def calculate(payload: CalorieInput) -> CalorieResultOut:
    """Stateless preview: compute from arbitrary inputs (the profile form preview)."""
    result = engine.compute(
        gender=payload.gender,
        weight_kg=payload.weight_kg,
        height_cm=payload.height_cm,
        age=payload.age,
        activity=payload.activity_level,
        goal=payload.goal,
    )
    return CalorieResultOut.model_validate(result)


@router.get("/me", response_model=CalorieResultOut)
def my_calories(session: SessionDep, user: CurrentUser) -> CalorieResultOut:
    """Compute from the saved profile."""
    profile = repository.get_profile(session, user.id)
    if profile is None:
        raise HTTPException(status_code=404, detail="profile not set")
    result = engine.compute(
        gender=profile.gender,
        weight_kg=profile.weight_kg,
        height_cm=profile.height_cm,
        age=profile.age,
        activity=profile.activity_level,
        goal=profile.goal,
    )
    return CalorieResultOut.model_validate(result)


@router.get("/activity-levels", response_model=list[ActivityLevelOut])
def activity_levels() -> list[ActivityLevelOut]:
    """The occupational ladder + multipliers, in dropdown order."""
    return [
        ActivityLevelOut(key=level, multiplier=multiplier)
        for level, multiplier in engine.MULTIPLIERS.items()
    ]
