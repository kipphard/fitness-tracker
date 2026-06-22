"""Library seeding: full import + FK-safe pruning of an older, smaller seed."""
from sqlalchemy import func, select

from backend.persistence.models import (
    Exercise,
    ExerciseSource,
    Routine,
    RoutineExercise,
    User,
)
from backend.workouts.library import LIBRARY_EXERCISES
from backend.workouts.seed import seed_library


def test_seed_prunes_unreferenced_legacy_keeps_used(session_factory):
    s = session_factory()
    # Two leftover lib exercises from an older seed (names not in the current library).
    unused = Exercise(owner_id=None, source=ExerciseSource.lib, name="Legacy Unused Lift")
    used = Exercise(owner_id=None, source=ExerciseSource.lib, name="Legacy Used Lift")
    s.add_all([unused, used])
    s.flush()
    unused_id, used_id = unused.id, used.id

    # `used` is referenced by a routine — deleting it would cascade away a routine
    # entry, so the prune must keep it.
    user = User(email="seed@test.dev", password_hash="x")
    s.add(user)
    s.flush()
    routine = Routine(user_id=user.id, name="Legacy")
    s.add(routine)
    s.flush()
    s.add(
        RoutineExercise(
            routine_id=routine.id, exercise_id=used_id, position=0, planned_sets=3
        )
    )
    s.commit()

    seed_library(s)  # lib_count (2) < library size -> upsert + prune

    names = {e.name for e in s.scalars(select(Exercise)).all()}
    assert "Legacy Unused Lift" not in names          # pruned (unreferenced)
    assert s.get(Exercise, unused_id) is None
    assert s.get(Exercise, used_id) is not None        # kept (referenced by routine)

    lib_count = s.scalar(
        select(func.count()).select_from(Exercise).where(
            Exercise.source == ExerciseSource.lib
        )
    )
    assert lib_count >= len(LIBRARY_EXERCISES)          # full library seeded
    assert "Barbell Squat" in names                     # a known library entry
    s.close()
