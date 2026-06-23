"""Pure unit tests for the deterministic fill-remaining-calories engine."""
import uuid
from decimal import Decimal

from backend.food.suggest import Candidate, suggest_foods


def _c(name, kcal, p, f, c):
    return Candidate(
        food_id=uuid.uuid4(),
        name=name,
        per100_kcal=Decimal(kcal),
        per100_protein_g=Decimal(p),
        per100_fat_g=Decimal(f),
        per100_carbs_g=Decimal(c),
    )


def test_portion_fills_remaining_kcal():
    # 100 kcal / 100 g, 250 kcal remaining → 250 g.
    [s] = suggest_foods(
        remaining_kcal=Decimal(250),
        protein_gap=Decimal(0),
        fat_gap=Decimal(0),
        carbs_gap=Decimal(0),
        candidates=[_c("Rice", 100, 2, 0, 22)],
    )
    assert s.amount_g == Decimal(250)
    assert s.kcal == Decimal(250)


def test_protein_gap_ranks_protein_dense_food_first():
    chicken = _c("Chicken", 165, 31, 4, 0)  # protein-dense
    candy = _c("Candy", 400, 0, 5, 95)      # carb/fat
    out = suggest_foods(
        remaining_kcal=Decimal(300),
        protein_gap=Decimal(40),  # big protein gap, no carb/fat need
        fat_gap=Decimal(0),
        carbs_gap=Decimal(0),
        candidates=[candy, chicken],  # deliberately list candy first
    )
    assert out[0].name == "Chicken"


def test_carb_gap_ranks_carb_food_first():
    chicken = _c("Chicken", 165, 31, 4, 0)
    rice = _c("Rice", 130, 2, 0, 28)
    out = suggest_foods(
        remaining_kcal=Decimal(300),
        protein_gap=Decimal(0),
        fat_gap=Decimal(0),
        carbs_gap=Decimal(60),  # carbs needed
        candidates=[chicken, rice],
    )
    assert out[0].name == "Rice"


def test_tiny_remaining_returns_nothing():
    assert (
        suggest_foods(
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
        suggest_foods(
            remaining_kcal=Decimal(500),
            protein_gap=Decimal(30),
            fat_gap=Decimal(10),
            carbs_gap=Decimal(40),
            candidates=[],
        )
        == []
    )


def test_low_energy_food_dropped():
    # Lettuce ~15 kcal/100g: even at the max 600 g portion that's only 90 kcal — far below
    # half of a 500 kcal gap → dropped.
    assert (
        suggest_foods(
            remaining_kcal=Decimal(500),
            protein_gap=Decimal(10),
            fat_gap=Decimal(0),
            carbs_gap=Decimal(20),
            candidates=[_c("Lettuce", 15, 1, 0, 3)],
        )
        == []
    )


def test_results_capped_and_carry_food_id():
    cands = [_c(f"Food{i}", 100 + i, 10, 5, 10) for i in range(10)]
    out = suggest_foods(
        remaining_kcal=Decimal(400),
        protein_gap=Decimal(20),
        fat_gap=Decimal(10),
        carbs_gap=Decimal(20),
        candidates=cands,
        max_results=6,
    )
    assert len(out) == 6
    assert all(s.food_id is not None for s in out)
