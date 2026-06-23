"""Pure unit tests for the deterministic fill-remaining-calories basket engine."""
import uuid
from decimal import Decimal

from backend.food.suggest import (
    GENERIC_MAX_G,
    MAX_SERVINGS,
    Candidate,
    realistic_portion,
    suggest_basket,
)


def _c(name, kcal, p, f, c, serving=None):
    return Candidate(
        food_id=uuid.uuid4(),
        name=name,
        per100_kcal=Decimal(kcal),
        per100_protein_g=Decimal(p),
        per100_fat_g=Decimal(f),
        per100_carbs_g=Decimal(c),
        serving_g=None if serving is None else Decimal(serving),
    )


# --- portion realism -------------------------------------------------------

def test_serving_food_capped_to_a_few_scoops():
    # Whey ~378 kcal/100g, 30 g scoop, huge budget → must NOT become 480 g.
    grams = realistic_portion(
        target_kcal=Decimal(1800),
        original_remaining=Decimal(1800),
        per100_kcal=Decimal(378),
        serving_g=Decimal(30),
    )
    assert grams <= MAX_SERVINGS * Decimal(30)  # at most 3 scoops
    assert grams == Decimal(90)


def test_servingless_food_capped_to_generic_max():
    grams = realistic_portion(
        target_kcal=Decimal(2000),
        original_remaining=Decimal(2000),
        per100_kcal=Decimal(150),
        serving_g=None,
    )
    assert grams <= GENERIC_MAX_G


def test_no_single_item_exceeds_calorie_share():
    # Even an energy-dense, serving-less food is capped to ≤60% of the original budget.
    grams = realistic_portion(
        target_kcal=Decimal(1000),
        original_remaining=Decimal(1000),
        per100_kcal=Decimal(900),  # oil-like
        serving_g=None,
    )
    assert Decimal(900) * grams / Decimal(100) <= Decimal(1000) * Decimal("0.6") + Decimal("1")


# --- basket composition ----------------------------------------------------

def test_basket_does_not_suggest_absurd_whey_portion():
    whey = _c("Whey Isolate", 378, 90, 1, 4, serving=30)
    out = suggest_basket(
        remaining_kcal=Decimal(1800),
        protein_gap=Decimal(190),
        fat_gap=Decimal(76),
        carbs_gap=Decimal(93),
        candidates=[whey],
    )
    assert all(s.amount_g <= MAX_SERVINGS * Decimal(30) for s in out)


def test_basket_combines_multiple_foods():
    whey = _c("Whey", 378, 90, 1, 4, serving=30)
    pasta = _c("Pasta bake", 191, 9, 10, 15)
    snickers = _c("Snickers", 485, 9, 25, 60, serving=50)
    out = suggest_basket(
        remaining_kcal=Decimal(1800),
        protein_gap=Decimal(190),
        fat_gap=Decimal(76),
        carbs_gap=Decimal(93),
        candidates=[whey, pasta, snickers],
    )
    assert len(out) >= 2  # spread across foods, not one giant portion
    assert len({s.name for s in out}) == len(out)  # no food repeated


def test_protein_gap_picks_protein_food_first():
    chicken = _c("Chicken", 165, 31, 4, 0)
    rice = _c("Rice", 130, 2, 0, 28)
    out = suggest_basket(
        remaining_kcal=Decimal(600),
        protein_gap=Decimal(60),
        fat_gap=Decimal(0),
        carbs_gap=Decimal(0),
        candidates=[rice, chicken],  # rice listed first on purpose
    )
    assert out[0].name == "Chicken"


def test_tiny_remaining_returns_nothing():
    assert (
        suggest_basket(
            remaining_kcal=Decimal(30),
            protein_gap=Decimal(10),
            fat_gap=Decimal(5),
            carbs_gap=Decimal(5),
            candidates=[_c("Rice", 130, 2, 0, 28)],
        )
        == []
    )


def test_no_candidates_returns_nothing():
    assert (
        suggest_basket(
            remaining_kcal=Decimal(500),
            protein_gap=Decimal(30),
            fat_gap=Decimal(10),
            carbs_gap=Decimal(40),
            candidates=[],
        )
        == []
    )


def test_basket_capped_at_max_items_and_carries_food_id():
    cands = [_c(f"Food{i}", 150, 10, 5, 12) for i in range(10)]
    out = suggest_basket(
        remaining_kcal=Decimal(3000),
        protein_gap=Decimal(120),
        fat_gap=Decimal(60),
        carbs_gap=Decimal(200),
        candidates=cands,
    )
    assert 0 < len(out) <= 4
    assert all(s.food_id is not None for s in out)
