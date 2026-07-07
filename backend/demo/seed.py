"""Generative demo-data seed for the public live demo.

``seed_demo_for_user`` builds a realistic recent history for one user, reusing the normal
repository helpers + engines (so the data is exactly what the app would have produced). It is
**idempotent per user**: it first clears the user's own generated rows, then re-creates them, so
re-running (or re-seeding a preview account) yields the same dataset with no duplicates.

Used by both the public ``POST /api/auth/demo`` endpoint (per-visitor sandbox) and the
``python -m backend.seed_demo <email>`` CLI (standing preview account). Touches only the given
user's rows — never another user's data.
"""
from __future__ import annotations

import random
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.calories.engine import ActivityLevel, Gender, Goal
from backend.food.scale import scale_per100
from backend.persistence import repository
from backend.persistence.models import (
    BodyMeasurement,
    Food,
    FoodLog,
    FoodSource,
    Language,
    MealSlot,
    Routine,
    RoutineExercise,
    SetLog,
    SetType,
    StepLog,
    UnitSystem,
    WeighIn,
    WorkoutSession,
)
from backend.workouts.seed import seed_library

DAYS = 45

# (name, per100 kcal, protein, fat, carbs, serving_g)
_FOODS: list[tuple[str, str, str, str, str, str]] = [
    ("Oats", "380", "13", "7", "60", "60"),
    ("Whole milk", "64", "3.4", "3.6", "4.7", "200"),
    ("Banana", "89", "1.1", "0.3", "23", "120"),
    ("Chicken breast", "165", "31", "3.6", "0", "150"),
    ("Basmati rice (cooked)", "130", "2.7", "0.3", "28", "180"),
    ("Broccoli", "34", "2.8", "0.4", "7", "150"),
    ("Greek yogurt 0%", "59", "10", "0.4", "3.6", "170"),
    ("Almonds", "579", "21", "50", "22", "30"),
    ("Salmon fillet", "208", "20", "13", "0", "150"),
    ("Whole-grain bread", "247", "13", "4", "41", "60"),
    ("Eggs", "155", "13", "11", "1.1", "120"),
    ("Olive oil", "884", "0", "100", "0", "10"),
]

# Which foods fill which meal, and a typical gram amount.
_MEALS: dict[MealSlot, list[tuple[str, int]]] = {
    MealSlot.breakfast: [("Oats", 60), ("Whole milk", 200), ("Banana", 120)],
    MealSlot.lunch: [("Chicken breast", 160), ("Basmati rice (cooked)", 180), ("Broccoli", 150)],
    MealSlot.dinner: [("Salmon fillet", 150), ("Whole-grain bread", 60), ("Eggs", 120)],
    MealSlot.snack: [("Greek yogurt 0%", 170), ("Almonds", 30)],
}


def _clear_user_demo_data(session: Session, user_id: uuid.UUID) -> None:
    """Delete the user's generated rows in child→parent order (works regardless of whether the
    DB enforces FK cascades — SQLite in tests does not by default)."""
    session_ids = select(WorkoutSession.id).where(WorkoutSession.user_id == user_id)
    routine_ids = select(Routine.id).where(Routine.user_id == user_id)
    session.execute(delete(SetLog).where(SetLog.session_id.in_(session_ids)))
    session.execute(delete(WorkoutSession).where(WorkoutSession.user_id == user_id))
    session.execute(delete(RoutineExercise).where(RoutineExercise.routine_id.in_(routine_ids)))
    session.execute(delete(Routine).where(Routine.user_id == user_id))
    session.execute(delete(FoodLog).where(FoodLog.user_id == user_id))
    session.execute(delete(BodyMeasurement).where(BodyMeasurement.user_id == user_id))
    session.execute(delete(StepLog).where(StepLog.user_id == user_id))
    session.execute(delete(WeighIn).where(WeighIn.user_id == user_id))
    session.execute(delete(Food).where(Food.owner_id == user_id))
    session.flush()


def seed_demo_for_user(
    session: Session, user_id: uuid.UUID, *, today: date | None = None
) -> None:
    """Idempotently seed ~45 days of realistic history for ``user_id``. Commits at the end."""
    today = today or date.today()
    rng = random.Random(user_id.int & 0xFFFFFFFF)  # deterministic-but-varied per user

    seed_library(session)  # idempotent; ensures library exercises exist to reference
    _clear_user_demo_data(session, user_id)

    repository.upsert_profile(
        session,
        user_id,
        height_cm=Decimal("181"),
        age=31,
        gender=Gender.male,
        weight_kg=Decimal("83.5"),
        activity_level=ActivityLevel.moderately_active,
        goal=Goal.cut,
    )
    repository.upsert_settings(
        session,
        user_id,
        language=Language.en,
        unit_system=UnitSystem.metric,
        eat_back_activity=True,
        country="Germany",
        store="REWE",
        dietary_preferences="No pork; high protein",
        food_budget_weekly=Decimal("70"),
        currency="EUR",
    )
    repository.upsert_macro_target(
        session, user_id, protein_g_per_kg=Decimal("2.0"), fat_g_per_kg=Decimal("0.8")
    )

    # Weigh-ins: gentle downtrend with daily noise.
    start_w = 86.0
    for i in range(DAYS + 1):
        d = today - timedelta(days=DAYS - i)
        w = start_w - i * 0.06 + rng.uniform(-0.3, 0.3)
        repository.upsert_weigh_in(session, user_id, d, Decimal(f"{w:.1f}"))

    # Foods (the user's catalogue), reused across the diary.
    foods: dict[str, Food] = {}
    for name, kcal, p, f, c, serving in _FOODS:
        foods[name] = repository.create_food(
            session,
            user_id,
            source=FoodSource.custom,
            name=name,
            per100_kcal=Decimal(kcal),
            per100_protein_g=Decimal(p),
            per100_fat_g=Decimal(f),
            per100_carbs_g=Decimal(c),
            serving_g=Decimal(serving),
        )

    # Food logs across meal slots, with a few missed days/snacks for realism.
    for i in range(DAYS + 1):
        d = today - timedelta(days=DAYS - i)
        if rng.random() < 0.12:
            continue
        for slot, items in _MEALS.items():
            if slot == MealSlot.snack and rng.random() < 0.4:
                continue
            for fname, base in items:
                food = foods[fname]
                amount = Decimal(int(base * rng.uniform(0.85, 1.15)))
                sc = scale_per100(
                    per100_kcal=food.per100_kcal,
                    per100_protein_g=food.per100_protein_g,
                    per100_fat_g=food.per100_fat_g,
                    per100_carbs_g=food.per100_carbs_g,
                    amount_g=amount,
                )
                repository.create_food_log(
                    session,
                    user_id,
                    date=d,
                    slot=slot.value,  # store the plain slot key (column is now free-text)
                    food_id=food.id,
                    food_name=food.name,
                    amount_g=amount,
                    kcal=sc.kcal,
                    protein_g=sc.protein_g,
                    fat_g=sc.fat_g,
                    carbs_g=sc.carbs_g,
                )

    # Steps.
    for i in range(DAYS + 1):
        d = today - timedelta(days=DAYS - i)
        repository.upsert_step_log(session, user_id, d, rng.randint(6000, 13000))

    # Routines from the library (fall back to the first available exercises if names differ).
    lib = [e for e in repository.search_exercises(session, user_id, "", limit=2000) if e.owner_id is None]

    def pick(*names: str):
        out = []
        for n in names:
            m = next((e for e in lib if e.name == n), None) or next(
                (e for e in lib if n.lower() in e.name.lower()), None
            )
            if m is not None and m not in out:
                out.append(m)
        return out

    upper = pick("Barbell Bench Press - Medium Grip", "Pullups", "Overhead Press", "Barbell Curl")
    lower = pick("Barbell Squat", "Romanian Deadlift", "Leg Press", "Standing Calf Raises")
    if len(upper) < 3:
        upper = lib[:4]
    if len(lower) < 3:
        lower = lib[4:8]

    routines = []
    for rname, exs, reps in [("Upper A", upper, 8), ("Lower A", lower, 6)]:
        r = repository.create_routine(session, user_id, rname)
        for pos, ex in enumerate(exs):
            repository.add_routine_exercise(
                session, r, ex.id, position=pos, planned_sets=3, planned_reps=reps
            )
        routines.append((r, exs, reps))

    # Backdated completed sessions: 3×/week for ~4 weeks, alternating the two routines.
    schedule = [(week, dow) for week in range(4) for dow in (0, 2, 4)]
    for idx, (week, dow) in enumerate(schedule):
        days_ago = (3 - week) * 7 + (6 - dow)
        started = datetime(
            (today - timedelta(days=days_ago)).year,
            (today - timedelta(days=days_ago)).month,
            (today - timedelta(days=days_ago)).day,
            18, 0, tzinfo=timezone.utc,
        )
        routine, exs, reps = routines[idx % 2]
        ws = repository.create_workout_session(
            session, user_id, routine_id=routine.id, routine_name=routine.name, started_at=started
        )
        for ex in exs:
            base = rng.choice([40, 50, 60, 70, 80, 100])
            for si in range(1, 4):
                repository.add_set(
                    session,
                    ws.id,
                    exercise_id=ex.id,
                    exercise_name=ex.name,
                    set_index=si,
                    weight=Decimal(str(base + idx)),
                    reps=reps + rng.randint(-1, 1),
                    set_type=SetType.working,
                    rpe=Decimal("8"),
                )
        ws.ended_at = started + timedelta(minutes=rng.randint(40, 75))
        session.flush()

    # Body measurements, weekly.
    for week in range(5):
        d = today - timedelta(days=(4 - week) * 7)
        repository.upsert_measurement(
            session,
            user_id,
            d,
            waist_cm=Decimal(f"{88 - week * 0.4:.1f}"),
            chest_cm=Decimal("104"),
            arm_cm=Decimal(f"{38 + week * 0.1:.1f}"),
            notes="weekly check",
        )

    session.commit()
