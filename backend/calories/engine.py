"""Pure calorie engine — the core of Phase 1.

Mifflin-St Jeor BMR (Grundumsatz) × an occupational activity factor gives the daily
maintenance need (TDEE). A goal adjustment turns maintenance into the eating target, and a
calorie floor guards against extreme deficits (master plan §13).

This module is *pure*: no database, no FastAPI, no I/O. It owns the calorie-domain enums
(``Gender``, ``Goal``, ``ActivityLevel``); the SQLAlchemy models import them for their
columns. The occupational activity factor reflects job/lifestyle only — deliberate exercise
and steps are added per-day in a later phase, not here.

All values are :class:`~decimal.Decimal`, never ``float``.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class Gender(str, Enum):
    male = "male"
    female = "female"


class Goal(str, Enum):
    cut = "cut"
    maintain = "maintain"
    bulk = "bulk"


class ActivityLevel(str, Enum):
    """Occupational / lifestyle activity — job and daily life only, NOT deliberate
    exercise or steps. Ordered desk job -> heavy labor for the dropdown."""

    sedentary = "sedentary"
    lightly_active = "lightly_active"
    moderately_active = "moderately_active"
    heavy = "heavy"
    very_heavy = "very_heavy"


# Classic Mifflin/Harris activity multipliers for the occupational ladder.
# Insertion order is the dropdown order (desk job -> very heavy labor).
MULTIPLIERS: dict[ActivityLevel, Decimal] = {
    ActivityLevel.sedentary: Decimal("1.2"),
    ActivityLevel.lightly_active: Decimal("1.375"),
    ActivityLevel.moderately_active: Decimal("1.55"),
    ActivityLevel.heavy: Decimal("1.725"),
    ActivityLevel.very_heavy: Decimal("1.9"),
}

# Goal-adjusted target offsets (kcal/day) applied to maintenance.
CUT_DEFICIT_KCAL = Decimal("500")
BULK_SURPLUS_KCAL = Decimal("300")

GOAL_ADJUSTMENT: dict[Goal, Decimal] = {
    Goal.cut: -CUT_DEFICIT_KCAL,
    Goal.maintain: Decimal("0"),
    Goal.bulk: BULK_SURPLUS_KCAL,
}

# Safety guardrail: never recommend a target below a sensible floor (master plan §13).
CALORIE_FLOOR: dict[Gender, Decimal] = {
    Gender.male: Decimal("1500"),
    Gender.female: Decimal("1200"),
}


@dataclass(frozen=True)
class CalorieResult:
    """The full breakdown the API and UI report, all in kcal/day (Decimal)."""

    bmr: Decimal
    activity_multiplier: Decimal
    maintenance: Decimal
    goal_adjustment: Decimal
    target: Decimal
    floor: Decimal
    below_floor: bool


def _dec(value: Decimal | int | float | str) -> Decimal:
    """Coerce to Decimal without introducing binary-float artefacts."""
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal(value)


def bmr(
    *,
    gender: Gender,
    weight_kg: Decimal | int | float | str,
    height_cm: Decimal | int | float | str,
    age: int,
) -> Decimal:
    """Basal metabolic rate via Mifflin-St Jeor.

    men:   BMR = 10*kg + 6.25*cm - 5*age + 5
    women: BMR = 10*kg + 6.25*cm - 5*age - 161
    """
    base = (
        Decimal(10) * _dec(weight_kg)
        + Decimal("6.25") * _dec(height_cm)
        - Decimal(5) * _dec(age)
    )
    return base + (Decimal(5) if gender is Gender.male else Decimal(-161))


def maintenance(basal_metabolic_rate: Decimal, activity: ActivityLevel) -> Decimal:
    """Maintenance (TDEE) = BMR × occupational activity multiplier."""
    return _dec(basal_metabolic_rate) * MULTIPLIERS[activity]


def goal_target(maintenance_kcal: Decimal, gender: Gender, goal: Goal) -> Decimal:
    """Goal-adjusted eating target, clamped up to the calorie floor."""
    raw = _dec(maintenance_kcal) + GOAL_ADJUSTMENT[goal]
    return max(raw, CALORIE_FLOOR[gender])


def compute(
    *,
    gender: Gender,
    weight_kg: Decimal | int | float | str,
    height_cm: Decimal | int | float | str,
    age: int,
    activity: ActivityLevel,
    goal: Goal,
) -> CalorieResult:
    """Full BMR -> maintenance -> goal target pipeline with the floor guardrail."""
    basal = bmr(gender=gender, weight_kg=weight_kg, height_cm=height_cm, age=age)
    multiplier = MULTIPLIERS[activity]
    maint = basal * multiplier
    adjustment = GOAL_ADJUSTMENT[goal]
    raw_target = maint + adjustment
    floor = CALORIE_FLOOR[gender]
    return CalorieResult(
        bmr=basal,
        activity_multiplier=multiplier,
        maintenance=maint,
        goal_adjustment=adjustment,
        target=max(raw_target, floor),
        floor=floor,
        below_floor=raw_target < floor,
    )
