"""Live workout sessions + set logging (Phase 7)."""
from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Response

from backend.api.deps import CurrentUser, SessionDep
from backend.persistence import repository
from backend.schemas import (
    SessionStartIn,
    SetIn,
    SetOut,
    SetUpdateIn,
    WorkoutSessionOut,
    WorkoutSessionSummaryOut,
)
from backend.workouts.progression import set_volume

router = APIRouter(prefix="/workouts", tags=["workouts"])


@router.post("", response_model=WorkoutSessionOut, status_code=201)
def start_session(
    payload: SessionStartIn, session: SessionDep, user: CurrentUser
) -> WorkoutSessionOut:
    routine_name = None
    if payload.routine_id is not None:
        routine = repository.get_routine(session, payload.routine_id, user.id)
        if routine is None:
            raise HTTPException(status_code=404, detail="routine not found")
        routine_name = routine.name
    ws = repository.create_workout_session(
        session, user.id, routine_id=payload.routine_id, routine_name=routine_name
    )
    session.commit()
    return WorkoutSessionOut.model_validate(ws)


@router.get("", response_model=list[WorkoutSessionSummaryOut])
def list_sessions(
    session: SessionDep, user: CurrentUser
) -> list[WorkoutSessionSummaryOut]:
    out = []
    for ws in repository.list_workout_sessions(session, user.id):
        out.append(
            WorkoutSessionSummaryOut(
                id=ws.id,
                routine_name=ws.routine_name,
                started_at=ws.started_at,
                ended_at=ws.ended_at,
                set_count=len(ws.sets),
                total_volume=sum(
                    (set_volume(s.weight, s.reps) for s in ws.sets), Decimal(0)
                ),
            )
        )
    return out


@router.delete("/sets/{set_id}", status_code=204)
def delete_set(
    set_id: uuid.UUID, session: SessionDep, user: CurrentUser
) -> Response:
    log = repository.get_set(session, set_id, user.id)
    if log is not None:
        session.delete(log)
        session.commit()
    return Response(status_code=204)


@router.delete("/{session_id}", status_code=204)
def delete_session(
    session_id: uuid.UUID, session: SessionDep, user: CurrentUser
) -> Response:
    """Delete a whole workout session and its sets."""
    repository.delete_workout_session(session, session_id, user.id)
    session.commit()
    return Response(status_code=204)


@router.get("/{session_id}", response_model=WorkoutSessionOut)
def get_session_detail(
    session_id: uuid.UUID, session: SessionDep, user: CurrentUser
) -> WorkoutSessionOut:
    ws = repository.get_workout_session(session, session_id, user.id)
    if ws is None:
        raise HTTPException(status_code=404, detail="session not found")
    return WorkoutSessionOut.model_validate(ws)


@router.post("/{session_id}/sets", response_model=SetOut, status_code=201)
def log_set(
    session_id: uuid.UUID, payload: SetIn, session: SessionDep, user: CurrentUser
) -> SetOut:
    ws = repository.get_workout_session(session, session_id, user.id)
    if ws is None:
        raise HTTPException(status_code=404, detail="session not found")
    exercise = repository.get_exercise(session, payload.exercise_id, user.id)
    if exercise is None:
        raise HTTPException(status_code=400, detail="exercise not found")
    set_index = sum(1 for s in ws.sets if s.exercise_id == payload.exercise_id) + 1
    log = repository.add_set(
        session,
        session_id,
        exercise_id=payload.exercise_id,
        exercise_name=exercise.name,
        set_index=set_index,
        weight=payload.weight,
        reps=payload.reps,
        set_type=payload.set_type,
        rpe=payload.rpe,
    )
    session.commit()
    return SetOut.model_validate(log)


@router.patch("/{session_id}/sets/{set_id}", response_model=SetOut)
def update_set(
    session_id: uuid.UUID,
    set_id: uuid.UUID,
    payload: SetUpdateIn,
    session: SessionDep,
    user: CurrentUser,
) -> SetOut:
    """Edit a logged set (weight/reps/set_type/rpe) — only the sent fields are applied."""
    log = repository.get_set(session, set_id, user.id)
    if log is None or log.session_id != session_id:
        raise HTTPException(status_code=404, detail="set not found")
    repository.update_set(session, log, **payload.model_dump(exclude_unset=True))
    session.commit()
    return SetOut.model_validate(log)


@router.post("/{session_id}/finish", response_model=WorkoutSessionOut)
def finish_session(
    session_id: uuid.UUID, session: SessionDep, user: CurrentUser
) -> WorkoutSessionOut:
    ws = repository.get_workout_session(session, session_id, user.id)
    if ws is None:
        raise HTTPException(status_code=404, detail="session not found")
    repository.finish_workout_session(ws)
    session.commit()
    return WorkoutSessionOut.model_validate(ws)
