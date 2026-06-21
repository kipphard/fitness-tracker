"""SQLAlchemy 2.0 ORM models: users, profiles, settings (Phase 0).

The calorie-domain enums (Gender, Goal, ActivityLevel) are owned by the pure engine in
``backend.calories.engine`` and imported here for the column types. UI-only enums
(Language, UnitSystem) live here.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.calories.engine import ActivityLevel, Gender, Goal
from backend.persistence.database import Base
from backend.persistence.types import GUID, Measure


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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="settings")
