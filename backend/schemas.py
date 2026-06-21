"""Pydantic request/response DTOs for the REST API.

Decimals are serialized as JSON strings (Pydantic v2 default) to preserve precision — the
frontend parses them as strings.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from backend.calories.engine import ActivityLevel, Gender, Goal
from backend.persistence.models import Language, UnitSystem


# --- auth ---

class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# --- profile ---

class ProfileIn(BaseModel):
    height_cm: Decimal = Field(gt=0, le=300)
    age: int = Field(ge=0, le=130)
    gender: Gender
    weight_kg: Decimal = Field(gt=0, le=700)
    activity_level: ActivityLevel
    goal: Goal


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    height_cm: Decimal
    age: int
    gender: Gender
    weight_kg: Decimal
    activity_level: ActivityLevel
    goal: Goal
    created_at: datetime


# --- settings ---

class SettingsIn(BaseModel):
    language: Language | None = None
    unit_system: UnitSystem | None = None


class SettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    language: Language
    unit_system: UnitSystem


# --- calories ---

class CalorieInput(BaseModel):
    height_cm: Decimal = Field(gt=0, le=300)
    age: int = Field(ge=0, le=130)
    gender: Gender
    weight_kg: Decimal = Field(gt=0, le=700)
    activity_level: ActivityLevel
    goal: Goal


class CalorieResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    bmr: Decimal
    activity_multiplier: Decimal
    maintenance: Decimal
    goal_adjustment: Decimal
    target: Decimal
    floor: Decimal
    below_floor: bool


class ActivityLevelOut(BaseModel):
    key: ActivityLevel
    multiplier: Decimal
