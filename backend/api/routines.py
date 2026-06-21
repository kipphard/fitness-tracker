"""Workout routines / templates (Phase 7)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Response

from backend.api.deps import CurrentUser, SessionDep
from backend.persistence import repository
from backend.persistence.models import Routine
from backend.schemas import RoutineExerciseOut, RoutineIn, RoutineOut

router = APIRouter(prefix="/routines", tags=["routines"])


def _routine_out(routine: Routine) -> RoutineOut:
    return RoutineOut(
        id=routine.id,
        name=routine.name,
        exercises=[
            RoutineExerciseOut(
                exercise_id=re.exercise_id,
                exercise_name=re.exercise.name if re.exercise else "—",
                position=re.position,
                planned_sets=re.planned_sets,
                planned_reps=re.planned_reps,
            )
            for re in routine.exercises
        ],
    )


@router.post("", response_model=RoutineOut, status_code=201)
def create_routine(
    payload: RoutineIn, session: SessionDep, user: CurrentUser
) -> RoutineOut:
    routine = repository.create_routine(session, user.id, payload.name)
    for position, item in enumerate(payload.exercises):
        if repository.get_exercise(session, item.exercise_id, user.id) is None:
            raise HTTPException(status_code=400, detail="exercise not found")
        repository.add_routine_exercise(
            session,
            routine,
            item.exercise_id,
            position=position,
            planned_sets=item.planned_sets,
            planned_reps=item.planned_reps,
        )
    session.commit()
    session.refresh(routine)
    return _routine_out(routine)


@router.get("", response_model=list[RoutineOut])
def list_routines(session: SessionDep, user: CurrentUser) -> list[RoutineOut]:
    return [_routine_out(r) for r in repository.list_routines(session, user.id)]


@router.get("/{routine_id}", response_model=RoutineOut)
def get_routine(
    routine_id: uuid.UUID, session: SessionDep, user: CurrentUser
) -> RoutineOut:
    routine = repository.get_routine(session, routine_id, user.id)
    if routine is None:
        raise HTTPException(status_code=404, detail="routine not found")
    return _routine_out(routine)


@router.delete("/{routine_id}", status_code=204)
def delete_routine(
    routine_id: uuid.UUID, session: SessionDep, user: CurrentUser
) -> Response:
    repository.delete_routine(session, routine_id, user.id)
    session.commit()
    return Response(status_code=204)
