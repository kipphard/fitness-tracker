"""Deterministic "fill the remaining calories" suggester (issue #5, section 1).

Given the day's remaining kcal and macro gaps, pick foods + portions from the user's own
catalogue (recents first, then the rest of their saved foods) that close the gap. Each
candidate is sized to hit the remaining kcal, then ranked by how well its macro profile
matches what's still missing — a protein-heavy gap surfaces protein-dense foods first.

Pure and tested: no I/O, no network, no DB. All values are :class:`~decimal.Decimal`. The
AI-assisted variant (``suggest_ai``) reuses :func:`build_suggestion` so both paths emit the
same shape; the rule-based engine here is the always-on default and needs no API key.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from backend.food.scale import scale_per100

# Below this remaining budget there's nothing worth suggesting (you're essentially on target).
MIN_GAP_KCAL = Decimal(50)
# Portion bounds + rounding so suggested amounts are realistic and tidy.
MIN_PORTION_G = Decimal(10)
MAX_PORTION_G = Decimal(600)
PORTION_STEP_G = Decimal(5)
# Drop a food if, even at the max portion, it can't fill at least this fraction of the gap
# (filters out very low-energy foods that would never realistically close the budget).
MIN_FILL_RATIO = Decimal("0.5")
DEFAULT_MAX_RESULTS = 6


@dataclass(frozen=True)
class Candidate:
    """A food the user could eat, with per-100g nutrition. ``food_id`` lets the diary log it
    by reference (no duplicate row); list order encodes preference (recents first)."""

    food_id: uuid.UUID | None
    name: str
    per100_kcal: Decimal
    per100_protein_g: Decimal
    per100_fat_g: Decimal
    per100_carbs_g: Decimal


@dataclass(frozen=True)
class Suggestion:
    """A concrete portion of a food, with macros at that portion. Carries per-100g values so
    the frontend can log via ``food_id`` (saved food) or inline ``food`` (novel AI food)."""

    food_id: uuid.UUID | None
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


def _round_to_step(grams: Decimal) -> Decimal:
    steps = (grams / PORTION_STEP_G).to_integral_value(rounding=ROUND_HALF_UP)
    return steps * PORTION_STEP_G


def _cosine(a: tuple[Decimal, Decimal, Decimal], b: tuple[Decimal, Decimal, Decimal]) -> Decimal:
    """Cosine similarity of two non-negative macro vectors → [0, 1]. 0 if either is the zero
    vector. Scale-invariant, so it measures macro *direction* (the split), not magnitude."""
    dot = sum((x * y for x, y in zip(a, b)), Decimal(0))
    na = sum((x * x for x in a), Decimal(0)).sqrt()
    nb = sum((x * x for x in b), Decimal(0)).sqrt()
    if na == 0 or nb == 0:
        return Decimal(0)
    return dot / (na * nb)


def build_suggestion(
    *,
    food_id: uuid.UUID | None,
    name: str,
    amount_g: Decimal,
    per100_kcal: Decimal,
    per100_protein_g: Decimal,
    per100_fat_g: Decimal,
    per100_carbs_g: Decimal,
    reason: str = "",
) -> Suggestion:
    """Scale per-100g nutrition to the portion and package it as a :class:`Suggestion`."""
    scaled = scale_per100(
        per100_kcal=per100_kcal,
        per100_protein_g=per100_protein_g,
        per100_fat_g=per100_fat_g,
        per100_carbs_g=per100_carbs_g,
        amount_g=amount_g,
    )
    return Suggestion(
        food_id=food_id,
        name=name,
        amount_g=Decimal(amount_g),
        kcal=scaled.kcal,
        protein_g=scaled.protein_g,
        fat_g=scaled.fat_g,
        carbs_g=scaled.carbs_g,
        per100_kcal=Decimal(per100_kcal),
        per100_protein_g=Decimal(per100_protein_g),
        per100_fat_g=Decimal(per100_fat_g),
        per100_carbs_g=Decimal(per100_carbs_g),
        reason=reason,
    )


def suggest_foods(
    *,
    remaining_kcal: Decimal,
    protein_gap: Decimal,
    fat_gap: Decimal,
    carbs_gap: Decimal,
    candidates: list[Candidate],
    max_results: int = DEFAULT_MAX_RESULTS,
) -> list[Suggestion]:
    """Rank single-food suggestions that fill ``remaining_kcal``, best macro match first.

    Returns ``[]`` when the budget is essentially met (``remaining_kcal < MIN_GAP_KCAL``) or
    there are no usable candidates. The macro gaps steer the ranking; negative gaps (a macro
    already met) are treated as zero.
    """
    if remaining_kcal < MIN_GAP_KCAL:
        return []

    gap = (
        max(protein_gap, Decimal(0)),
        max(fat_gap, Decimal(0)),
        max(carbs_gap, Decimal(0)),
    )

    scored: list[tuple[Decimal, int, Candidate, Decimal]] = []
    for idx, c in enumerate(candidates):
        if c.per100_kcal <= 0:
            continue  # can't fill a kcal gap (and would divide by zero below)
        amount = _round_to_step(remaining_kcal / c.per100_kcal * Decimal(100))
        amount = min(max(amount, MIN_PORTION_G), MAX_PORTION_G)
        actual_kcal = c.per100_kcal * amount / Decimal(100)
        if actual_kcal < remaining_kcal * MIN_FILL_RATIO:
            continue  # even at the max portion it can't meaningfully close the gap
        food_vec = (c.per100_protein_g, c.per100_fat_g, c.per100_carbs_g)
        score = _cosine(food_vec, gap)
        scored.append((score, idx, c, amount))

    # Higher macro-fit first; round the score to 2dp so near-ties fall back to input order,
    # which keeps the more relevant recents ahead. `idx` makes the order fully deterministic.
    scored.sort(key=lambda t: (-t[0].quantize(Decimal("0.01")), t[1]))

    return [
        build_suggestion(
            food_id=c.food_id,
            name=c.name,
            amount_g=amount,
            per100_kcal=c.per100_kcal,
            per100_protein_g=c.per100_protein_g,
            per100_fat_g=c.per100_fat_g,
            per100_carbs_g=c.per100_carbs_g,
        )
        for _score, _idx, c, amount in scored[:max_results]
    ]
