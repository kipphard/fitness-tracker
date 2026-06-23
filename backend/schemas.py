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
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from backend.calories.engine import ActivityLevel, Gender, Goal
from backend.persistence.models import Language, MealSlot, SetType, UnitSystem


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
    # Food-planning preferences (issue #5 §2). "" clears a field; None leaves it unchanged.
    country: str | None = Field(default=None, max_length=80)
    store: str | None = Field(default=None, max_length=120)
    dietary_preferences: str | None = Field(default=None, max_length=500)
    # Food budget (issue #5 §4): weekly grocery spend + 3-letter currency code.
    food_budget_weekly: Decimal | None = Field(default=None, ge=0, le=100000)
    currency: str | None = Field(default=None, max_length=3)


class SettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    language: Language
    unit_system: UnitSystem
    eat_back_activity: bool
    country: str | None = None
    store: str | None = None
    dietary_preferences: str | None = None
    food_budget_weekly: Decimal | None = None
    currency: str | None = None


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
    # Adaptive TDEE (issue #4): `maintenance` above is the value actually used (blended once
    # enough data exists). These expose the breakdown — measured is null until the threshold.
    formula_maintenance: Decimal | None = None
    measured_maintenance: Decimal | None = None
    tdee_confidence: Decimal = Decimal(0)


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


class FoodUpdateIn(BaseModel):
    """Partial update of a saved food — chiefly to set a serving size after the fact. Only the
    fields present are applied (``model_dump(exclude_unset=True)``)."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    per100_kcal: Decimal | None = Field(default=None, ge=0, le=1000)
    per100_protein_g: Decimal | None = Field(default=None, ge=0, le=100)
    per100_fat_g: Decimal | None = Field(default=None, ge=0, le=100)
    per100_carbs_g: Decimal | None = Field(default=None, ge=0, le=100)
    serving_g: Decimal | None = Field(default=None, gt=0, le=5000)


class BackfillOut(BaseModel):
    checked: int
    updated: int


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
    workout_kcal: Decimal
    net_deficit_kcal: Decimal
    eat_back_activity: bool
    ai_available: bool = False  # whether Claude features are configured (no API key → False)


# --- pantry (issue #5 §2) ---

class PantryItemIn(BaseModel):
    food_id: uuid.UUID
    note: str | None = Field(default=None, max_length=200)


class PantryItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    note: str | None = None
    food: FoodOut


# --- shopping list (issue #5 §3) ---

class ShoppingItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    amount_g: Decimal | None = Field(default=None, gt=0, le=100000)
    price: Decimal | None = Field(default=None, ge=0, le=100000)


class ShoppingPlanItem(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    food_id: uuid.UUID | None = None
    amount_g: Decimal | None = Field(default=None, gt=0, le=100000)


class ShoppingFromPlanIn(BaseModel):
    items: list[ShoppingPlanItem]


class ShoppingPatchIn(BaseModel):
    # Both optional so a PATCH can tick an item off, set its price, or both. exclude_unset
    # distinguishes "not sent" from null in the endpoint.
    checked: bool | None = None
    price: Decimal | None = Field(default=None, ge=0, le=100000)


class ShoppingItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    food_id: uuid.UUID | None = None
    amount_g: Decimal | None = None
    price: Decimal | None = None
    checked: bool


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


# --- fill remaining calories (issue #5, section 1) ---

class SuggestIn(BaseModel):
    date: date_type | None = None  # defaults to today
    tz: int = Field(default=0, ge=-720, le=840)  # minutes east of UTC
    slot: MealSlot | None = None  # the meal we're filling — biases picks toward it
    exclude_food_ids: list[uuid.UUID] = Field(default_factory=list)  # skip these (regenerate)
    count: int | None = Field(default=None, ge=1, le=8)  # basket size override (1 = swap one)
    target_kcal: Decimal | None = Field(default=None, gt=0)  # size against this, not the day


class SuggestAiIn(SuggestIn):
    preferences: str | None = Field(default=None, max_length=500)


class SuggestionOut(BaseModel):
    """A suggested food + portion. ``food_id`` is set for the user's saved foods (log by
    reference); novel AI foods carry per-100g values so the diary can log them inline."""

    model_config = ConfigDict(from_attributes=True)

    food_id: uuid.UUID | None = None
    name: str
    amount_g: Decimal
    kcal: Decimal
    protein_g: Decimal
    fat_g: Decimal
    carbs_g: Decimal
    per100_kcal: Decimal
    per100_protein_g: Decimal
    per100_fat_g: Decimal
    per100_carbs_g: Decimal
    reason: str = ""


class SuggestOut(BaseModel):
    date: date_type
    remaining_kcal: Decimal
    protein_gap_g: Decimal
    fat_gap_g: Decimal
    carbs_gap_g: Decimal
    suggestions: list[SuggestionOut]
    ai_available: bool  # whether the AI path is configured (frontend shows the ✨ button)
    source: str  # "rule" | "ai"
    notes: str = ""


# --- day plan (issue #5, section 2) ---

class PlanIn(BaseModel):
    date: date_type | None = None  # defaults to today
    tz: int = Field(default=0, ge=-720, le=840)  # minutes east of UTC
    # full_day = a fresh blueprint to the day's whole target; remaining = only what's left.
    scope: Literal["full_day", "remaining"] = "full_day"
    meals: int = Field(default=4, ge=3, le=4)  # how many meals to split the day into
    preferences: str | None = Field(default=None, max_length=500)  # overrides saved prefs (AI)


class PlanMealOut(BaseModel):
    """One meal slot of the plan plus its slot totals."""

    slot: MealSlot
    suggestions: list[SuggestionOut]
    kcal: Decimal
    protein_g: Decimal
    fat_g: Decimal
    carbs_g: Decimal


class PlanOut(BaseModel):
    date: date_type
    scope: str
    target_kcal: Decimal  # the kcal the plan aims to fill (whole-day or remaining)
    meals: list[PlanMealOut]
    planned_kcal: Decimal  # what the plan's portions actually add up to
    planned_protein_g: Decimal
    planned_fat_g: Decimal
    planned_carbs_g: Decimal
    ai_available: bool  # whether the AI path is configured (frontend shows the ✨ button)
    source: str  # "rule" | "ai"
    notes: str = ""


# --- workouts (Phase 7) ---

class ExerciseIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    primary_muscles: list[str] = Field(default_factory=list)
    secondary_muscles: list[str] = Field(default_factory=list)
    equipment: str | None = Field(default=None, max_length=100)
    category: str | None = Field(default=None, max_length=50)
    instructions: str | None = None


class ExerciseListOut(BaseModel):
    """Lightweight library row for the picker — omits ``instructions`` (the library
    is ~870 exercises, so the full-text instructions would bloat the list payload)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: str
    name: str
    name_de: str | None = None
    primary_muscles: list[str] | None = None
    secondary_muscles: list[str] | None = None
    equipment: str | None = None
    category: str | None = None
    image_url: str | None = None


class ExerciseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: str
    name: str
    name_de: str | None = None
    primary_muscles: list[str] | None = None
    secondary_muscles: list[str] | None = None
    equipment: str | None = None
    category: str | None = None
    instructions: str | None = None
    image_url: str | None = None


class RoutineExerciseIn(BaseModel):
    exercise_id: uuid.UUID
    planned_sets: int = Field(default=3, ge=1, le=20)
    planned_reps: int | None = Field(default=None, ge=1, le=100)


class RoutineIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    exercises: list[RoutineExerciseIn] = Field(default_factory=list)


class RoutineExerciseOut(BaseModel):
    exercise_id: uuid.UUID
    exercise_name: str
    position: int
    planned_sets: int
    planned_reps: int | None = None


class RoutineOut(BaseModel):
    id: uuid.UUID
    name: str
    exercises: list[RoutineExerciseOut]


class SessionStartIn(BaseModel):
    routine_id: uuid.UUID | None = None


class SetIn(BaseModel):
    exercise_id: uuid.UUID
    weight: Decimal = Field(ge=0, le=2000)
    reps: int = Field(ge=0, le=1000)
    set_type: SetType = SetType.working
    rpe: Decimal | None = Field(default=None, ge=0, le=10)


class SetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    exercise_id: uuid.UUID | None = None
    exercise_name: str
    set_index: int
    weight: Decimal
    reps: int
    set_type: SetType
    rpe: Decimal | None = None


class WorkoutSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    routine_id: uuid.UUID | None = None
    routine_name: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    sets: list[SetOut]


class WorkoutSessionSummaryOut(BaseModel):
    id: uuid.UUID
    routine_name: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    set_count: int
    total_volume: Decimal


class ProgressionPointOut(BaseModel):
    date: datetime
    top_weight: Decimal
    volume: Decimal
    est_1rm: Decimal


class PRsOut(BaseModel):
    best_weight: Decimal
    best_est_1rm: Decimal


class ProgressionOut(BaseModel):
    exercise_id: uuid.UUID
    exercise_name: str
    points: list[ProgressionPointOut]
    prs: PRsOut | None = None


# --- body measurements + trends (Phase 8) ---

class MeasurementIn(BaseModel):
    date: date_type | None = None
    waist_cm: Decimal | None = Field(default=None, gt=0, le=300)
    chest_cm: Decimal | None = Field(default=None, gt=0, le=300)
    hips_cm: Decimal | None = Field(default=None, gt=0, le=300)
    arm_cm: Decimal | None = Field(default=None, gt=0, le=150)
    thigh_cm: Decimal | None = Field(default=None, gt=0, le=200)
    notes: str | None = Field(default=None, max_length=500)


class MeasurementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date_type
    waist_cm: Decimal | None = None
    chest_cm: Decimal | None = None
    hips_cm: Decimal | None = None
    arm_cm: Decimal | None = None
    thigh_cm: Decimal | None = None
    notes: str | None = None


class AdherenceDayOut(BaseModel):
    date: date_type
    consumed: Decimal
    target: Decimal


class WeeklyWeightOut(BaseModel):
    week_start: date_type
    average: Decimal


class TrendsOut(BaseModel):
    target_kcal: Decimal | None = None
    adherence: list[AdherenceDayOut]
    weekly_weight: list[WeeklyWeightOut]
    weekly_change_kg: Decimal | None = None
    rate_warning: bool
    # Adaptive TDEE (issue #4): measured vs. formula maintenance + confidence (0..1).
    formula_maintenance: Decimal | None = None
    measured_maintenance: Decimal | None = None
    tdee_confidence: Decimal = Decimal(0)
    tdee_days: int = 0
