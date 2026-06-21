"""Pydantic request/response DTOs for the REST API.

Decimals are serialized as JSON strings (Pydantic v2 default) to preserve precision — the
frontend parses them as strings.

Note: the ``date`` type is imported as ``date_type``. A field literally named ``date`` with a
default (``date: date | None = None``) makes ``date`` local to the class body, which would
shadow the type in the annotation; the alias avoids that while keeping the JSON field ``date``.
"""
import uuid
from datetime import date as date_type
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from backend.calories.engine import ActivityLevel, Gender, Goal
from backend.persistence.models import Language, MealSlot, UnitSystem


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
    eat_back_activity: bool | None = None


class SettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    language: Language
    unit_system: UnitSystem
    eat_back_activity: bool


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


class MyCaloriesOut(CalorieResultOut):
    """The saved-profile calorie result, plus which weight fed it (Phase 2 feedback)."""

    weight_kg: Decimal
    weight_source: str


class ActivityLevelOut(BaseModel):
    key: ActivityLevel
    multiplier: Decimal


# --- weight (Phase 2) ---

class WeighInIn(BaseModel):
    date: date_type | None = None  # defaults to today on the server
    weight_kg: Decimal = Field(gt=0, le=700)


class WeighInOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date_type
    weight_kg: Decimal


class TrendPointOut(BaseModel):
    date: date_type
    trend: Decimal


class WeekAverageOut(BaseModel):
    week_start: date_type
    average: Decimal
    count: int


class WeightTrendOut(BaseModel):
    points: list[WeighInOut]
    ewma: list[TrendPointOut]
    weekly: list[WeekAverageOut]
    current_trend: Decimal | None = None
    effective_weight: Decimal | None = None
    effective_source: str | None = None


# --- macros + today (Phase 3) ---

class MacroPrefIn(BaseModel):
    protein_g_per_kg: Decimal | None = Field(default=None, gt=0, le=10)
    fat_g_per_kg: Decimal | None = Field(default=None, gt=0, le=10)


class MacroPrefOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    protein_g_per_kg: Decimal
    fat_g_per_kg: Decimal


class MacroResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    protein_g: Decimal
    fat_g: Decimal
    carbs_g: Decimal
    protein_kcal: Decimal
    fat_kcal: Decimal
    carbs_kcal: Decimal
    target_kcal: Decimal
    reconciled: bool
    over_kcal: Decimal


# --- food + diary (Phase 4) ---

class FoodIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    per100_kcal: Decimal = Field(ge=0, le=1000)
    per100_protein_g: Decimal = Field(default=Decimal(0), ge=0, le=100)
    per100_fat_g: Decimal = Field(default=Decimal(0), ge=0, le=100)
    per100_carbs_g: Decimal = Field(default=Decimal(0), ge=0, le=100)
    serving_g: Decimal | None = Field(default=None, gt=0, le=5000)
    barcode: str | None = Field(default=None, max_length=50)


class FoodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: str
    barcode: str | None = None
    name: str
    per100_kcal: Decimal
    per100_protein_g: Decimal
    per100_fat_g: Decimal
    per100_carbs_g: Decimal
    serving_g: Decimal | None = None


class FoodDataOut(BaseModel):
    """A transient Open Food Facts search result (not yet persisted; has no id)."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    barcode: str | None = None
    per100_kcal: Decimal
    per100_protein_g: Decimal
    per100_fat_g: Decimal
    per100_carbs_g: Decimal
    serving_g: Decimal | None = None


class ConsumedOut(BaseModel):
    kcal: Decimal
    protein_g: Decimal
    fat_g: Decimal
    carbs_g: Decimal


class DiaryIn(BaseModel):
    date: date_type | None = None  # defaults to today
    slot: MealSlot
    amount_g: Decimal = Field(gt=0, le=5000)
    food_id: uuid.UUID | None = None
    food: FoodIn | None = None  # inline custom food when food_id is absent


class DiaryUpdateIn(BaseModel):
    amount_g: Decimal | None = Field(default=None, gt=0, le=5000)
    slot: MealSlot | None = None


class DiaryEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    date: date_type
    slot: MealSlot
    food_id: uuid.UUID | None = None
    food_name: str
    amount_g: Decimal
    kcal: Decimal
    protein_g: Decimal
    fat_g: Decimal
    carbs_g: Decimal


class DiaryDayOut(BaseModel):
    date: date_type
    entries: list[DiaryEntryOut]
    totals: ConsumedOut


class DiaryCopyIn(BaseModel):
    from_date: date_type
    to_date: date_type | None = None


class StepsIn(BaseModel):
    date: date_type | None = None  # defaults to today
    steps: int = Field(ge=0, le=200000)


class StepsOut(BaseModel):
    date: date_type
    steps: int
    kcal: Decimal  # derived from the effective weight


class TodayOut(BaseModel):
    date: date_type
    calories: MyCaloriesOut
    macros: MacroResultOut
    consumed: ConsumedOut
    remaining_kcal: Decimal
    steps: int
    activity_kcal: Decimal
    net_deficit_kcal: Decimal
    eat_back_activity: bool


# --- photo estimation (Phase 5) ---

class EstimateItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    amount_g: Decimal
    kcal: Decimal
    protein_g: Decimal
    fat_g: Decimal
    carbs_g: Decimal


class MacroTotalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kcal: Decimal
    protein_g: Decimal
    fat_g: Decimal
    carbs_g: Decimal


class PhotoEstimateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[EstimateItemOut]
    total: MacroTotalOut
    confidence: str
    questions: list[str]
    notes: str
