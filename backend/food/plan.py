"""Deterministic full-day meal planner (issue #5, section 2).

Where :mod:`backend.food.suggest` fills the day's *remaining* calories with one basket, this
splits a whole-day (or remaining) kcal + macro target across a few meal slots and fills each
slot from the user's own foods using that same single-basket suggester. The always-on rule
path: needs no API key. The AI variant (:mod:`backend.food.suggest_ai`) layers store-aware
realistic products on top once Claude is configured.

Pure and tested: no I/O, no network, no DB. All values are :class:`~decimal.Decimal`.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal

from backend.food.suggest import Candidate, Suggestion, suggest_basket

# How the day's budget is shared across meals, keyed by meal count. Each list's shares sum to 1.
MEAL_SPLITS: dict[int, list[tuple[str, Decimal]]] = {
    3: [
        ("breakfast", Decimal("0.30")),
        ("lunch", Decimal("0.40")),
        ("dinner", Decimal("0.30")),
    ],
    4: [
        ("breakfast", Decimal("0.25")),
        ("lunch", Decimal("0.35")),
        ("dinner", Decimal("0.30")),
        ("snack", Decimal("0.10")),
    ],
}

DEFAULT_MEALS = 4
# A meal is a couple of foods, a snack just one or two — keep each slot from ballooning.
ITEMS_PER_MEAL = 3
ITEMS_PER_SNACK = 2


@dataclass(frozen=True)
class PlannedMeal:
    """One meal slot of the day plan and the foods chosen to fill it (possibly empty)."""

    slot: str
    suggestions: list[Suggestion]


def meal_split(meals: int) -> list[tuple[str, Decimal]]:
    """The slot/percentage split for ``meals`` meals, falling back to the 4-meal default."""
    return MEAL_SPLITS.get(meals) or MEAL_SPLITS[DEFAULT_MEALS]


def plan_day(
    *,
    kcal_budget: Decimal,
    protein_target: Decimal,
    fat_target: Decimal,
    carbs_target: Decimal,
    candidates_by_slot: dict[str, list[Candidate]],
    meals: int = DEFAULT_MEALS,
) -> list[PlannedMeal]:
    """Compose a full day of meals whose portions together approach the day's targets.

    The budget and macro targets are split per :data:`MEAL_SPLITS`, then each slot is filled by
    the single-basket suggester from that slot's candidate pool (so breakfast biases toward
    breakfast foods). A food placed in an earlier slot is dropped from later slots so the day
    varies (no oats + yogurt three times); with a small catalogue later slots may underfill.
    Slots with no usable candidates — or a per-slot share below the suggester's minimum — come
    back empty rather than failing.
    """
    plan: list[PlannedMeal] = []
    used: set[uuid.UUID] = set()
    for slot, pct in meal_split(meals):
        max_items = ITEMS_PER_SNACK if slot == "snack" else ITEMS_PER_MEAL
        pool = [c for c in candidates_by_slot.get(slot, []) if c.food_id not in used]
        suggestions = suggest_basket(
            remaining_kcal=kcal_budget * pct,
            protein_gap=protein_target * pct,
            fat_gap=fat_target * pct,
            carbs_gap=carbs_target * pct,
            candidates=pool,
            max_items=max_items,
            slot=slot,
        )
        for s in suggestions:
            if s.food_id is not None:
                used.add(s.food_id)
        plan.append(PlannedMeal(slot=slot, suggestions=suggestions))
    return plan
