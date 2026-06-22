"""Query helpers. Everything is user-scoped."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.persistence.models import (
    BodyMeasurement,
    Exercise,
    ExerciseSource,
    Food,
    FoodLog,
    MacroTarget,
    Profile,
    Routine,
    RoutineExercise,
    SetLog,
    Settings,
    StepLog,
    User,
    WeighIn,
    WorkoutSession,
)
from backend.workouts.seed import seed_library


# --- users ---

def create_user(session: Session, *, email: str, password_hash: str) -> User:
    user = User(email=email, password_hash=password_hash)
    session.add(user)
    session.flush()
    return user


def get_user(session: Session, user_id: uuid.UUID) -> User | None:
    return session.get(User, user_id)


def get_user_by_email(session: Session, email: str) -> User | None:
    return session.scalar(select(User).where(User.email == email))


# --- profile (1:1) ---

def get_profile(session: Session, user_id: uuid.UUID) -> Profile | None:
    return session.scalar(select(Profile).where(Profile.user_id == user_id))


def upsert_profile(session: Session, user_id: uuid.UUID, **fields: Any) -> Profile:
    profile = get_profile(session, user_id)
    if profile is None:
        profile = Profile(user_id=user_id, **fields)
        session.add(profile)
    else:
        for key, value in fields.items():
            setattr(profile, key, value)
    session.flush()
    return profile


# --- settings (1:1) ---

def get_settings(session: Session, user_id: uuid.UUID) -> Settings | None:
    return session.scalar(select(Settings).where(Settings.user_id == user_id))


def upsert_settings(session: Session, user_id: uuid.UUID, **fields: Any) -> Settings:
    settings = get_settings(session, user_id)
    if settings is None:
        settings = Settings(user_id=user_id, **fields)
        session.add(settings)
    else:
        for key, value in fields.items():
            setattr(settings, key, value)
    session.flush()
    return settings


# --- weigh-ins (one per user+date) ---

def list_weigh_ins(session: Session, user_id: uuid.UUID) -> list[WeighIn]:
    """All weigh-ins for a user, oldest first (the order the trend math expects)."""
    return list(
        session.scalars(
            select(WeighIn).where(WeighIn.user_id == user_id).order_by(WeighIn.date)
        )
    )


def upsert_weigh_in(
    session: Session, user_id: uuid.UUID, day: date, weight_kg: Any
) -> WeighIn:
    weigh_in = session.scalar(
        select(WeighIn).where(WeighIn.user_id == user_id, WeighIn.date == day)
    )
    if weigh_in is None:
        weigh_in = WeighIn(user_id=user_id, date=day, weight_kg=weight_kg)
        session.add(weigh_in)
    else:
        weigh_in.weight_kg = weight_kg
    session.flush()
    return weigh_in


def delete_weigh_in(session: Session, user_id: uuid.UUID, day: date) -> bool:
    weigh_in = session.scalar(
        select(WeighIn).where(WeighIn.user_id == user_id, WeighIn.date == day)
    )
    if weigh_in is None:
        return False
    session.delete(weigh_in)
    return True


# --- macro targets (1:1) ---

def get_macro_target(session: Session, user_id: uuid.UUID) -> MacroTarget | None:
    return session.scalar(select(MacroTarget).where(MacroTarget.user_id == user_id))


def upsert_macro_target(
    session: Session, user_id: uuid.UUID, **fields: Any
) -> MacroTarget:
    macro = get_macro_target(session, user_id)
    if macro is None:
        macro = MacroTarget(user_id=user_id, **fields)
        session.add(macro)
    else:
        for key, value in fields.items():
            setattr(macro, key, value)
    session.flush()
    return macro


# --- foods (per-user catalogue: custom + OFF cache) ---

def create_food(session: Session, owner_id: uuid.UUID, **fields: Any) -> Food:
    food = Food(owner_id=owner_id, **fields)
    session.add(food)
    session.flush()
    return food


def get_food(session: Session, food_id: uuid.UUID, owner_id: uuid.UUID) -> Food | None:
    food = session.get(Food, food_id)
    if food is None or food.owner_id != owner_id:
        return None
    return food


def get_food_by_barcode(
    session: Session, owner_id: uuid.UUID, barcode: str
) -> Food | None:
    return session.scalar(
        select(Food).where(Food.owner_id == owner_id, Food.barcode == barcode)
    )


def search_foods(
    session: Session, owner_id: uuid.UUID, query: str, limit: int = 20
) -> list[Food]:
    return list(
        session.scalars(
            select(Food)
            .where(Food.owner_id == owner_id, Food.name.ilike(f"%{query}%"))
            .order_by(Food.name)
            .limit(limit)
        )
    )


# --- diary (food logs) ---

def create_food_log(session: Session, user_id: uuid.UUID, **fields: Any) -> FoodLog:
    log = FoodLog(user_id=user_id, **fields)
    session.add(log)
    session.flush()
    return log


def list_food_logs(
    session: Session, user_id: uuid.UUID, day: date
) -> list[FoodLog]:
    return list(
        session.scalars(
            select(FoodLog)
            .where(FoodLog.user_id == user_id, FoodLog.date == day)
            .order_by(FoodLog.created_at)
        )
    )


def daily_intake(
    session: Session, user_id: uuid.UUID, start: date, end: date
) -> dict[date, Decimal]:
    """Total kcal logged per day over [start, end] (only days with logs). For adaptive TDEE."""
    rows = session.execute(
        select(FoodLog.date, func.sum(FoodLog.kcal))
        .where(FoodLog.user_id == user_id, FoodLog.date >= start, FoodLog.date <= end)
        .group_by(FoodLog.date)
    ).all()
    return {d: Decimal(total) for d, total in rows}


def get_food_log(
    session: Session, log_id: uuid.UUID, user_id: uuid.UUID
) -> FoodLog | None:
    log = session.get(FoodLog, log_id)
    if log is None or log.user_id != user_id:
        return None
    return log


def delete_food_log(session: Session, log_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    log = get_food_log(session, log_id, user_id)
    if log is None:
        return False
    session.delete(log)
    return True


def recent_foods(
    session: Session, user_id: uuid.UUID, limit: int = 10
) -> list[Food]:
    """Distinct foods from the user's most recent log entries (for quick re-logging)."""
    food_ids = session.execute(
        select(FoodLog.food_id)
        .where(FoodLog.user_id == user_id, FoodLog.food_id.isnot(None))
        .order_by(FoodLog.created_at.desc())
    ).scalars()
    ordered: list[uuid.UUID] = []
    for food_id in food_ids:
        if food_id not in ordered:
            ordered.append(food_id)
        if len(ordered) >= limit:
            break
    if not ordered:
        return []
    by_id = {f.id: f for f in session.scalars(select(Food).where(Food.id.in_(ordered)))}
    return [by_id[fid] for fid in ordered if fid in by_id]


# --- steps (one per user+date) ---

def get_step_log(session: Session, user_id: uuid.UUID, day: date) -> StepLog | None:
    return session.scalar(
        select(StepLog).where(StepLog.user_id == user_id, StepLog.date == day)
    )


def upsert_step_log(
    session: Session, user_id: uuid.UUID, day: date, steps: int
) -> StepLog:
    log = get_step_log(session, user_id, day)
    if log is None:
        log = StepLog(user_id=user_id, date=day, steps=steps)
        session.add(log)
    else:
        log.steps = steps
    session.flush()
    return log


def list_step_logs(session: Session, user_id: uuid.UUID) -> list[StepLog]:
    return list(
        session.scalars(
            select(StepLog).where(StepLog.user_id == user_id).order_by(StepLog.date)
        )
    )


# --- exercises (global library + per-user custom) ---

def search_exercises(
    session: Session, user_id: uuid.UUID, query: str = "", limit: int = 2000
) -> list[Exercise]:
    seed_library(session)
    stmt = select(Exercise).where(
        or_(Exercise.owner_id.is_(None), Exercise.owner_id == user_id)
    )
    if query.strip():
        stmt = stmt.where(Exercise.name.ilike(f"%{query.strip()}%"))
    return list(session.scalars(stmt.order_by(Exercise.name).limit(limit)))


def get_exercise(
    session: Session, exercise_id: uuid.UUID, user_id: uuid.UUID
) -> Exercise | None:
    ex = session.get(Exercise, exercise_id)
    if ex is None or (ex.owner_id is not None and ex.owner_id != user_id):
        return None
    return ex


def create_custom_exercise(
    session: Session, owner_id: uuid.UUID, **fields: Any
) -> Exercise:
    ex = Exercise(owner_id=owner_id, source=ExerciseSource.custom, **fields)
    session.add(ex)
    session.flush()
    return ex


# --- routines ---

def create_routine(session: Session, user_id: uuid.UUID, name: str) -> Routine:
    routine = Routine(user_id=user_id, name=name)
    session.add(routine)
    session.flush()
    return routine


def get_routine(
    session: Session, routine_id: uuid.UUID, user_id: uuid.UUID
) -> Routine | None:
    routine = session.get(Routine, routine_id)
    if routine is None or routine.user_id != user_id:
        return None
    return routine


def list_routines(session: Session, user_id: uuid.UUID) -> list[Routine]:
    return list(
        session.scalars(
            select(Routine).where(Routine.user_id == user_id).order_by(Routine.name)
        )
    )


def delete_routine(session: Session, routine_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    routine = get_routine(session, routine_id, user_id)
    if routine is None:
        return False
    session.delete(routine)
    return True


def add_routine_exercise(
    session: Session, routine: Routine, exercise_id: uuid.UUID, **fields: Any
) -> RoutineExercise:
    re = RoutineExercise(routine_id=routine.id, exercise_id=exercise_id, **fields)
    session.add(re)
    session.flush()
    return re


# --- workout sessions + sets ---

def create_workout_session(
    session: Session, user_id: uuid.UUID, **fields: Any
) -> WorkoutSession:
    ws = WorkoutSession(user_id=user_id, **fields)
    session.add(ws)
    session.flush()
    return ws


def get_workout_session(
    session: Session, session_id: uuid.UUID, user_id: uuid.UUID
) -> WorkoutSession | None:
    ws = session.get(WorkoutSession, session_id)
    if ws is None or ws.user_id != user_id:
        return None
    return ws


def list_workout_sessions(
    session: Session, user_id: uuid.UUID, limit: int = 50
) -> list[WorkoutSession]:
    return list(
        session.scalars(
            select(WorkoutSession)
            .where(WorkoutSession.user_id == user_id)
            .order_by(WorkoutSession.started_at.desc())
            .limit(limit)
        )
    )


def list_workout_sessions_between(
    session: Session,
    user_id: uuid.UUID,
    start: datetime,
    end: datetime,
) -> list[WorkoutSession]:
    """Sessions started in the half-open UTC window [start, end) — for one calendar day."""
    return list(
        session.scalars(
            select(WorkoutSession)
            .where(
                WorkoutSession.user_id == user_id,
                WorkoutSession.started_at >= start,
                WorkoutSession.started_at < end,
            )
            .order_by(WorkoutSession.started_at)
        )
    )


def finish_workout_session(ws: WorkoutSession) -> WorkoutSession:
    ws.ended_at = datetime.now(timezone.utc)
    return ws


def add_set(session: Session, session_id: uuid.UUID, **fields: Any) -> SetLog:
    log = SetLog(session_id=session_id, **fields)
    session.add(log)
    session.flush()
    return log


def get_set(session: Session, set_id: uuid.UUID, user_id: uuid.UUID) -> SetLog | None:
    log = session.get(SetLog, set_id)
    if log is None:
        return None
    ws = session.get(WorkoutSession, log.session_id)
    if ws is None or ws.user_id != user_id:
        return None
    return log


def last_sets_for_exercise(
    session: Session,
    user_id: uuid.UUID,
    exercise_id: uuid.UUID,
    exclude_session_id: uuid.UUID,
) -> list[SetLog]:
    """Sets for this exercise from the most recent *other* session (the 'last time')."""
    prior = session.execute(
        select(WorkoutSession.id)
        .join(SetLog, SetLog.session_id == WorkoutSession.id)
        .where(
            WorkoutSession.user_id == user_id,
            SetLog.exercise_id == exercise_id,
            WorkoutSession.id != exclude_session_id,
        )
        .order_by(WorkoutSession.started_at.desc())
        .limit(1)
    ).scalar()
    if prior is None:
        return []
    return list(
        session.scalars(
            select(SetLog)
            .where(SetLog.session_id == prior, SetLog.exercise_id == exercise_id)
            .order_by(SetLog.set_index)
        )
    )


def exercise_sets_with_dates(
    session: Session, user_id: uuid.UUID, exercise_id: uuid.UUID
) -> list[tuple[SetLog, datetime]]:
    """Every set for an exercise across the user's sessions, with the session start time."""
    rows = session.execute(
        select(SetLog, WorkoutSession.started_at)
        .join(WorkoutSession, SetLog.session_id == WorkoutSession.id)
        .where(WorkoutSession.user_id == user_id, SetLog.exercise_id == exercise_id)
        .order_by(WorkoutSession.started_at, SetLog.set_index)
    ).all()
    return [(row[0], row[1]) for row in rows]


# --- body measurements (one per user+date) ---

def get_measurement(
    session: Session, user_id: uuid.UUID, day: date
) -> BodyMeasurement | None:
    return session.scalar(
        select(BodyMeasurement).where(
            BodyMeasurement.user_id == user_id, BodyMeasurement.date == day
        )
    )


def upsert_measurement(
    session: Session, user_id: uuid.UUID, day: date, **fields: Any
) -> BodyMeasurement:
    row = get_measurement(session, user_id, day)
    if row is None:
        row = BodyMeasurement(user_id=user_id, date=day, **fields)
        session.add(row)
    else:
        for key, value in fields.items():
            setattr(row, key, value)
    session.flush()
    return row


def list_measurements(session: Session, user_id: uuid.UUID) -> list[BodyMeasurement]:
    return list(
        session.scalars(
            select(BodyMeasurement)
            .where(BodyMeasurement.user_id == user_id)
            .order_by(BodyMeasurement.date)
        )
    )
