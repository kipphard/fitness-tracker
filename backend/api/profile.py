"""Profile: the per-user body metrics + goal that feed the calorie engine."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.api.deps import CurrentUser, SessionDep
from backend.persistence import repository
from backend.schemas import ProfileIn, ProfileOut

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileOut)
def read_profile(session: SessionDep, user: CurrentUser) -> ProfileOut:
    profile = repository.get_profile(session, user.id)
    if profile is None:
        raise HTTPException(status_code=404, detail="profile not set")
    return ProfileOut.model_validate(profile)


@router.put("", response_model=ProfileOut)
def update_profile(
    payload: ProfileIn, session: SessionDep, user: CurrentUser
) -> ProfileOut:
    profile = repository.upsert_profile(
        session,
        user.id,
        height_cm=payload.height_cm,
        age=payload.age,
        gender=payload.gender,
        weight_kg=payload.weight_kg,
        activity_level=payload.activity_level,
        goal=payload.goal,
    )
    session.commit()
    return ProfileOut.model_validate(profile)
