"""Exercise library + custom exercises, last-time performance, and progression (Phase 7)."""
from __future__ import annotations

import uuid
from collections import OrderedDict
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query

from backend.api.deps import CurrentUser, SessionDep
from backend.persistence import repository
from backend.persistence.models import SetType
from backend.schemas import (
    ExerciseIn,
    ExerciseListOut,
    ExerciseOut,
    PRsOut,
    ProgressionOut,
    ProgressionPointOut,
    SetOut,
)
from backend.workouts.progression import epley_1rm, set_volume

router = APIRouter(prefix="/exercises", tags=["exercises"])

_ZERO_UUID = uuid.UUID(int=0)


@router.get("", response_model=list[ExerciseListOut])
def list_exercises(
    session: SessionDep, user: CurrentUser, q: str = ""
) -> list[ExerciseListOut]:
    # The library is large (~870); the picker doesn't render instructions, so the
    # lightweight ExerciseListOut omits them to keep the list payload small.
    return [
        ExerciseListOut.model_validate(e)
        for e in repository.search_exercises(session, user.id, q)
    ]


@router.post("", response_model=ExerciseOut, status_code=201)
def create_exercise(
    payload: ExerciseIn, session: SessionDep, user: CurrentUser
) -> ExerciseOut:
    ex = repository.create_custom_exercise(
        session,
        user.id,
        name=payload.name,
        primary_muscles=payload.primary_muscles,
        secondary_muscles=payload.secondary_muscles,
        equipment=payload.equipment,
        category=payload.category,
        instructions=payload.instructions,
    )
    session.commit()
    return ExerciseOut.model_validate(ex)


@router.get("/{exercise_id}/last", response_model=list[SetOut])
def last_time(
    exercise_id: uuid.UUID,
    session: SessionDep,
    user: CurrentUser,
    exclude: uuid.UUID | None = Query(default=None),
) -> list[SetOut]:
    """The sets logged for this exercise in the most recent *other* session."""
    if repository.get_exercise(session, exercise_id, user.id) is None:
        raise HTTPException(status_code=404, detail="exercise not found")
    sets = repository.last_sets_for_exercise(
        session, user.id, exercise_id, exclude or _ZERO_UUID
    )
    return [SetOut.model_validate(s) for s in sets]


@router.get("/{exercise_id}/progression", response_model=ProgressionOut)
def progression(
    exercise_id: uuid.UUID, session: SessionDep, user: CurrentUser
) -> ProgressionOut:
    exercise = repository.get_exercise(session, exercise_id, user.id)
    if exercise is None:
        raise HTTPException(status_code=404, detail="exercise not found")

    groups: "OrderedDict[datetime, list]" = OrderedDict()
    for set_log, started in repository.exercise_sets_with_dates(
        session, user.id, exercise_id
    ):
        groups.setdefault(started, []).append(set_log)

    points: list[ProgressionPointOut] = []
    best_weight = Decimal(0)
    best_1rm = Decimal(0)
    for started, sets in groups.items():
        working = [s for s in sets if s.set_type == SetType.working] or sets
        top_weight = max((s.weight for s in working), default=Decimal(0))
        volume = sum((set_volume(s.weight, s.reps) for s in sets), Decimal(0))
        est = max((epley_1rm(s.weight, s.reps) for s in working), default=Decimal(0))
        points.append(
            ProgressionPointOut(
                date=started, top_weight=top_weight, volume=volume, est_1rm=est
            )
        )
        best_weight = max(best_weight, top_weight)
        best_1rm = max(best_1rm, est)

    prs = (
        PRsOut(best_weight=best_weight, best_est_1rm=best_1rm) if points else None
    )
    return ProgressionOut(
        exercise_id=exercise_id,
        exercise_name=exercise.name,
        points=points,
        prs=prs,
    )
