"""Idempotent seeding of the global exercise library."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.persistence.models import Exercise, ExerciseSource
from backend.workouts.library import LIBRARY_EXERCISES


def seed_library(session: Session) -> None:
    """Insert the curated library once. Re-runnable: a no-op if any lib exercise exists."""
    already = session.scalar(
        select(Exercise.id).where(Exercise.source == ExerciseSource.lib).limit(1)
    )
    if already is not None:
        return
    for ex in LIBRARY_EXERCISES:
        session.add(
            Exercise(
                owner_id=None,
                source=ExerciseSource.lib,
                name=ex["name"],
                primary_muscles=ex.get("primary_muscles", []),
                secondary_muscles=ex.get("secondary_muscles", []),
                equipment=ex.get("equipment"),
                category=ex.get("category"),
                instructions=ex.get("instructions"),
            )
        )
    # Commit so the one-time seed persists even when triggered from a read-only request.
    session.commit()
