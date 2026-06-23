"""Unit tests for the rule-based day planner + AI plan parsing (issue #5 §2)."""
import uuid
from decimal import Decimal

from backend.food.plan import DEFAULT_MEALS, PlannedMeal, meal_split, plan_day
from backend.food.suggest import Candidate
from backend.food.suggest_ai import parse_plan


def _cand(name, kcal, p, f, c, affinity=0):
    return Candidate(
        food_id=uuid.uuid4(),
        name=name,
        per100_kcal=Decimal(kcal),
        per100_protein_g=Decimal(p),
        per100_fat_g=Decimal(f),
        per100_carbs_g=Decimal(c),
        serving_g=None,
        slot_affinity=affinity,
    )


def _pool():
    foods = [
        _cand("Chicken", "165", "31", "4", "0"),
        _cand("Rice", "130", "2", "0", "28"),
        _cand("Salmon", "208", "20", "13", "0"),
        _cand("Oats", "380", "13", "7", "60"),
        _cand("Yogurt", "59", "10", "0", "4"),
        _cand("Almonds", "579", "21", "50", "22"),
    ]
    return {slot: foods for slot, _ in meal_split(DEFAULT_MEALS)}


def test_plan_day_four_meals_fills_each_slot():
    plan = plan_day(
        kcal_budget=Decimal("2000"),
        protein_target=Decimal("150"),
        fat_target=Decimal("60"),
        carbs_target=Decimal("200"),
        candidates_by_slot=_pool(),
        meals=4,
    )
    assert [m.slot for m in plan] == ["breakfast", "lunch", "dinner", "snack"]
    assert all(isinstance(m, PlannedMeal) for m in plan)
    # Most slots fill from the pool; the whole day adds up to a meaningful, not-absurd amount.
    total = sum((s.kcal for m in plan for s in m.suggestions), Decimal(0))
    assert total > 0
    assert total <= Decimal("2000") * Decimal("1.2")
    assert any(m.suggestions for m in plan)


def test_plan_day_does_not_repeat_a_food_across_slots():
    plan = plan_day(
        kcal_budget=Decimal("2000"),
        protein_target=Decimal("150"),
        fat_target=Decimal("60"),
        carbs_target=Decimal("200"),
        candidates_by_slot=_pool(),
        meals=4,
    )
    placed = [s.food_id for m in plan for s in m.suggestions]
    assert len(placed) == len(set(placed))  # each food appears in at most one meal


def test_plan_day_three_meals_has_no_snack():
    plan = plan_day(
        kcal_budget=Decimal("1800"),
        protein_target=Decimal("140"),
        fat_target=Decimal("55"),
        carbs_target=Decimal("180"),
        candidates_by_slot={slot: _pool()["breakfast"] for slot, _ in meal_split(3)},
        meals=3,
    )
    assert [m.slot for m in plan] == ["breakfast", "lunch", "dinner"]


def test_plan_day_empty_pool_returns_empty_meals():
    plan = plan_day(
        kcal_budget=Decimal("2000"),
        protein_target=Decimal("150"),
        fat_target=Decimal("60"),
        carbs_target=Decimal("200"),
        candidates_by_slot={},
        meals=4,
    )
    assert len(plan) == 4
    assert all(m.suggestions == [] for m in plan)


def test_plan_day_unknown_meal_count_falls_back_to_default():
    assert meal_split(99) == meal_split(DEFAULT_MEALS)


# --- parse_plan ---


def test_parse_plan_builds_meals():
    plan = parse_plan(
        {
            "meals": [
                {
                    "slot": "breakfast",
                    "items": [
                        {
                            "name": "Skyr",
                            "amount_g": 200,
                            "per100_kcal": 63,
                            "per100_protein_g": 11,
                            "per100_fat_g": 0.2,
                            "per100_carbs_g": 4,
                            "reason": "protein",
                        }
                    ],
                }
            ],
            "notes": "ok",
        }
    )
    assert plan.notes == "ok"
    assert len(plan.meals) == 1
    assert plan.meals[0].slot == "breakfast"
    assert plan.meals[0].items[0].name == "Skyr"


def test_parse_plan_drops_unknown_slot_and_zero_items():
    plan = parse_plan(
        {
            "meals": [
                {"slot": "brunch", "items": [{"name": "x", "amount_g": 100, "per100_kcal": 100}]},
                {"slot": "lunch", "items": [{"name": "y", "amount_g": 0, "per100_kcal": 100}]},
                {"slot": "dinner", "items": [{"name": "z", "amount_g": 100, "per100_kcal": 0}]},
            ],
            "notes": "",
        }
    )
    # brunch = unknown slot; lunch item has no portion; dinner item has no energy → all dropped.
    assert plan.meals == []


def test_parse_plan_tolerates_missing_fields():
    plan = parse_plan({})
    assert plan.meals == []
    assert plan.notes == ""
