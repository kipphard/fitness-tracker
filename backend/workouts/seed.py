"""Idempotent seeding of the global exercise library."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.persistence.models import (
    Exercise,
    ExerciseSource,
    RoutineExercise,
    SetLog,
)
from backend.workouts.library import LIBRARY_EXERCISES


def _fields(ex: dict) -> dict:
    return {
        "name": ex["name"],
        "name_de": ex.get("name_de"),
        "primary_muscles": ex.get("primary_muscles", []),
        "secondary_muscles": ex.get("secondary_muscles", []),
        "equipment": ex.get("equipment"),
        "category": ex.get("category"),
        "instructions": ex.get("instructions"),
        "image_url": ex.get("image_url"),
    }


def seed_library(session: Session) -> None:
    """Upsert the global library by name. Re-runnable and FK-safe.

    Runs the full upsert only when fewer lib rows exist than the library defines
    (a fresh DB, or the older 23-exercise seed being upgraded); a no-op once
    seeded. Existing lib rows are updated in place — never deleted — so routines
    and logged sets keep their ``exercise_id`` references intact.
    """
    lib_count = (
        session.scalar(
            select(func.count())
            .select_from(Exercise)
            .where(Exercise.source == ExerciseSource.lib)
        )
        or 0
    )
    if lib_count >= len(LIBRARY_EXERCISES):
        return

    existing = {
        e.name: e
        for e in session.scalars(
            select(Exercise).where(Exercise.source == ExerciseSource.lib)
        )
    }
    for ex in LIBRARY_EXERCISES:
        row = existing.get(ex["name"])
        if row is None:
            session.add(Exercise(owner_id=None, source=ExerciseSource.lib, **_fields(ex)))
        else:
            for key, value in _fields(ex).items():
                setattr(row, key, value)
    _prune_stale(session, existing.values())
    # Commit so the seed persists even when triggered from a read-only request.
    session.commit()


def _prune_stale(session: Session, prior_lib) -> None:
    """Drop leftover library exercises from an earlier, smaller seed that the current
    library no longer defines — but only when nothing references them.

    A row referenced by a routine (FK cascades) or by a logged set is kept so the
    user never loses a routine entry or progression history; everything else is a
    stale duplicate cluttering the picker and is removed.
    """
    library_names = {ex["name"] for ex in LIBRARY_EXERCISES}
    stale = [e for e in prior_lib if e.name not in library_names]
    if not stale:
        return
    stale_ids = [e.id for e in stale]
    referenced = set(
        session.scalars(
            select(RoutineExercise.exercise_id).where(
                RoutineExercise.exercise_id.in_(stale_ids)
            )
        )
    )
    referenced.update(
        session.scalars(
            select(SetLog.exercise_id).where(SetLog.exercise_id.in_(stale_ids))
        )
    )
    for e in stale:
        if e.id not in referenced:
            session.delete(e)
