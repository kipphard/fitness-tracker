"""Calorie engine unit tests — known values for BMR, every activity multiplier,
every goal adjustment, and the floor guardrail."""
from decimal import Decimal

import pytest

from backend.calories import engine
from backend.calories.engine import ActivityLevel, Gender, Goal

# Reference subject: 80 kg, 180 cm, 30 y.
MALE_BMR = Decimal("1780")  # 10*80 + 6.25*180 - 5*30 + 5
FEMALE_BMR = Decimal("1614")  # 10*80 + 6.25*180 - 5*30 - 161


def test_bmr_male():
    assert (
        engine.bmr(gender=Gender.male, weight_kg=Decimal("80"), height_cm=Decimal("180"), age=30)
        == MALE_BMR
    )


def test_bmr_female():
    assert (
        engine.bmr(gender=Gender.female, weight_kg=Decimal("80"), height_cm=Decimal("180"), age=30)
        == FEMALE_BMR
    )


@pytest.mark.parametrize(
    "level,expected",
    [
        (ActivityLevel.sedentary, "2136.0"),  # 1780 * 1.2
        (ActivityLevel.lightly_active, "2447.5"),  # 1780 * 1.375
        (ActivityLevel.moderately_active, "2759.0"),  # 1780 * 1.55
        (ActivityLevel.heavy, "3070.5"),  # 1780 * 1.725
        (ActivityLevel.very_heavy, "3382.0"),  # 1780 * 1.9
    ],
)
def test_maintenance_each_multiplier(level, expected):
    assert engine.maintenance(MALE_BMR, level) == Decimal(expected)


@pytest.mark.parametrize(
    "goal,expected",
    [
        (Goal.cut, "1636"),  # 2136 - 500
        (Goal.maintain, "2136"),  # unchanged
        (Goal.bulk, "2436"),  # 2136 + 300
    ],
)
def test_goal_target_each_goal(goal, expected):
    assert engine.goal_target(Decimal("2136"), Gender.male, goal) == Decimal(expected)


def test_compute_pipeline_male_sedentary_cut():
    r = engine.compute(
        gender=Gender.male,
        weight_kg=Decimal("80"),
        height_cm=Decimal("180"),
        age=30,
        activity=ActivityLevel.sedentary,
        goal=Goal.cut,
    )
    assert r.bmr == MALE_BMR
    assert r.activity_multiplier == Decimal("1.2")
    assert r.maintenance == Decimal("2136.0")
    assert r.goal_adjustment == Decimal("-500")
    assert r.target == Decimal("1636.0")
    assert r.floor == Decimal("1500")
    assert r.below_floor is False


def test_calorie_floor_clamps_extreme_deficit():
    # Small subject whose cut target falls below the female floor (1200).
    r = engine.compute(
        gender=Gender.female,
        weight_kg=Decimal("45"),
        height_cm=Decimal("150"),
        age=60,
        activity=ActivityLevel.sedentary,
        goal=Goal.cut,
    )
    assert r.maintenance == Decimal("1111.8")  # 926.5 * 1.2
    assert r.below_floor is True
    assert r.target == Decimal("1200")
    assert r.floor == Decimal("1200")
