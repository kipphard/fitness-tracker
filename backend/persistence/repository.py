"""Query helpers. Everything is user-scoped."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.persistence.models import (
    Food,
    FoodLog,
    MacroTarget,
    Profile,
    Settings,
    StepLog,
    User,
    WeighIn,
)


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
