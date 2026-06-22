"""SQLAlchemy 2.0 ORM models: users, profiles, settings (Phase 0).

The calorie-domain enums (Gender, Goal, ActivityLevel) are owned by the pure engine in
``backend.calories.engine`` and imported here for the column types. UI-only enums
(Language, UnitSystem) live here.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.calories.engine import ActivityLevel, Gender, Goal
from backend.macros.engine import DEFAULT_FAT_G_PER_KG, DEFAULT_PROTEIN_G_PER_KG
from backend.persistence.database import Base
from backend.persistence.types import GUID, JSONType, Macro, Measure


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Language(str, PyEnum):
    en = "en"
    de = "de"


class UnitSystem(str, PyEnum):
    metric = "metric"
    imperial = "imperial"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    profile: Mapped["Profile | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    settings: Mapped["Settings | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    weigh_ins: Mapped[list["WeighIn"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    macro_target: Mapped["MacroTarget | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class Profile(Base):
    """1:1 with a user. weight_kg lives here in Phase 1; Phase 2 adds weigh-ins."""

    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    height_cm: Mapped[Decimal] = mapped_column(Measure, nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[Gender] = mapped_column(Enum(Gender, name="gender"), nullable=False)
    weight_kg: Mapped[Decimal] = mapped_column(Measure, nullable=False)
    activity_level: Mapped[ActivityLevel] = mapped_column(
        Enum(ActivityLevel, name="activity_level"), nullable=False
    )
    goal: Mapped[Goal] = mapped_column(Enum(Goal, name="goal"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="profile")


class Settings(Base):
    """1:1 with a user: language + unit preferences."""

    __tablename__ = "settings"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    language: Mapped[Language] = mapped_column(
        Enum(Language, name="language"), nullable=False, default=Language.en
    )
    unit_system: Mapped[UnitSystem] = mapped_column(
        Enum(UnitSystem, name="unit_system"), nullable=False, default=UnitSystem.metric
    )
    # Whether step/workout activity calories are added back to the eating budget (Phase 6).
    eat_back_activity: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="settings")


class WeighIn(Base):
    """A single daily weigh-in. At most one per (user, date) — re-logging a day updates it."""

    __tablename__ = "weigh_ins"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_weigh_ins_user_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    weight_kg: Mapped[Decimal] = mapped_column(Measure, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="weigh_ins")


class MacroTarget(Base):
    """1:1 with a user. Protein and fat are set per kg of bodyweight; carbs fill the rest."""

    __tablename__ = "macro_targets"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    protein_g_per_kg: Mapped[Decimal] = mapped_column(
        Measure, nullable=False, default=DEFAULT_PROTEIN_G_PER_KG
    )
    fat_g_per_kg: Mapped[Decimal] = mapped_column(
        Measure, nullable=False, default=DEFAULT_FAT_G_PER_KG
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="macro_target")


class FoodSource(str, PyEnum):
    off = "off"
    custom = "custom"


class MealSlot(str, PyEnum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"


class Food(Base):
    """A food (custom or cached from Open Food Facts), scoped to its owner.

    Nutrition is stored per 100 g; logging scales it by the grams eaten.
    """

    __tablename__ = "foods"
    __table_args__ = (
        UniqueConstraint("owner_id", "barcode", name="uq_foods_owner_barcode"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source: Mapped[FoodSource] = mapped_column(
        Enum(FoodSource, name="food_source"), nullable=False
    )
    barcode: Mapped[str | None] = mapped_column(String(50), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    per100_kcal: Mapped[Decimal] = mapped_column(Measure, nullable=False)
    per100_protein_g: Mapped[Decimal] = mapped_column(Measure, nullable=False, default=0)
    per100_fat_g: Mapped[Decimal] = mapped_column(Measure, nullable=False, default=0)
    per100_carbs_g: Mapped[Decimal] = mapped_column(Measure, nullable=False, default=0)
    serving_g: Mapped[Decimal | None] = mapped_column(Measure, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )


class FoodLog(Base):
    """A single diary entry. Macros are denormalized at log time so history is stable
    even if the underlying food is later edited or deleted."""

    __tablename__ = "food_logs"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    slot: Mapped[MealSlot] = mapped_column(Enum(MealSlot, name="meal_slot"), nullable=False)
    food_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("foods.id", ondelete="SET NULL"), nullable=True
    )
    food_name: Mapped[str] = mapped_column(String(200), nullable=False)
    amount_g: Mapped[Decimal] = mapped_column(Measure, nullable=False)
    kcal: Mapped[Decimal] = mapped_column(Macro, nullable=False)
    protein_g: Mapped[Decimal] = mapped_column(Macro, nullable=False)
    fat_g: Mapped[Decimal] = mapped_column(Macro, nullable=False)
    carbs_g: Mapped[Decimal] = mapped_column(Macro, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )


class StepLog(Base):
    """Daily step count (one per user+date). Calories are derived on read from the effective
    weight, so they always reflect the current weight. A generic ingestion point — manual entry
    now, Health Connect / HealthKit later."""

    __tablename__ = "step_logs"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_step_logs_user_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    steps: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )


class ExerciseSource(str, PyEnum):
    lib = "lib"
    custom = "custom"


class SetType(str, PyEnum):
    warmup = "warmup"
    working = "working"


class Exercise(Base):
    """An exercise: a global library entry (owner_id NULL, source=lib) or a user's custom one."""

    __tablename__ = "exercises"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    source: Mapped[ExerciseSource] = mapped_column(
        Enum(ExerciseSource, name="exercise_source"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_de: Mapped[str | None] = mapped_column(String(200), nullable=True)
    primary_muscles: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    secondary_muscles: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    equipment: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Relative free-exercise-db image path (e.g. "Barbell_Squat/0.jpg"); the frontend
    # prefixes a CDN/self-host base. NULL for user-created custom exercises.
    image_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )


class Routine(Base):
    __tablename__ = "routines"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    exercises: Mapped[list["RoutineExercise"]] = relationship(
        back_populates="routine",
        cascade="all, delete-orphan",
        order_by="RoutineExercise.position",
    )


class RoutineExercise(Base):
    __tablename__ = "routine_exercises"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    routine_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("routines.id", ondelete="CASCADE"), nullable=False, index=True
    )
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    planned_sets: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    planned_reps: Mapped[int | None] = mapped_column(Integer, nullable=True)

    routine: Mapped["Routine"] = relationship(back_populates="exercises")
    exercise: Mapped["Exercise"] = relationship()


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    routine_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("routines.id", ondelete="SET NULL"), nullable=True
    )
    routine_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    sets: Mapped[list["SetLog"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="SetLog.created_at",
    )


class SetLog(Base):
    """One logged set. exercise_name is denormalized so history survives exercise deletion."""

    __tablename__ = "set_logs"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("workout_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exercise_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("exercises.id", ondelete="SET NULL"), nullable=True, index=True
    )
    exercise_name: Mapped[str] = mapped_column(String(200), nullable=False)
    set_index: Mapped[int] = mapped_column(Integer, nullable=False)
    weight: Mapped[Decimal] = mapped_column(Measure, nullable=False)
    reps: Mapped[int] = mapped_column(Integer, nullable=False)
    set_type: Mapped[SetType] = mapped_column(
        Enum(SetType, name="set_type"), nullable=False, default=SetType.working
    )
    rpe: Mapped[Decimal | None] = mapped_column(Numeric(3, 1), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    session: Mapped["WorkoutSession"] = relationship(back_populates="sets")


class BodyMeasurement(Base):
    """Body circumference measurements (cm), one row per user+date (Phase 8). All optional."""

    __tablename__ = "body_measurements"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_body_measurements_user_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    waist_cm: Mapped[Decimal | None] = mapped_column(Measure, nullable=True)
    chest_cm: Mapped[Decimal | None] = mapped_column(Measure, nullable=True)
    hips_cm: Mapped[Decimal | None] = mapped_column(Measure, nullable=True)
    arm_cm: Mapped[Decimal | None] = mapped_column(Measure, nullable=True)
    thigh_cm: Mapped[Decimal | None] = mapped_column(Measure, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
