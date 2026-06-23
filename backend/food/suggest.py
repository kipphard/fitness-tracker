"""Deterministic "fill the remaining calories" suggester (issue #5, section 1).

Given the day's remaining kcal and macro gaps, compose a small *basket* of foods from the
user's own catalogue (recents first, then the rest of their saved foods) whose realistic
portions together close the gap — picking foods that best fill the biggest remaining macro
need at each step (protein-heavy gap → protein-dense food first).

The key to staying realistic: portions respect each food's serving size and a per-item
calorie cap, so no single food is ever sized to swallow the whole day (no 480 g of whey).
A big remaining budget becomes a few sensible portions, not one absurd one.

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
# A basket is a few foods, not a feast; cap how many we compose.
MAX_BASKET_ITEMS = 4
# Portion realism. Serving-size foods snap to whole servings (capped); the rest fall back to a
# tidy gram amount bounded by a generic max. A per-item calorie cap stops any one food from
# dominating, which is what forces variety instead of "one food = the whole day".
MAX_SERVINGS = 3
GENERIC_MAX_G = Decimal(350)
MIN_PORTION_G = Decimal(10)
PORTION_STEP_G = Decimal(5)
MIN_ITEM_KCAL = Decimal(40)  # skip a food whose realistic portion barely moves the needle
MAX_ITEM_KCAL_SHARE = Decimal("0.6")  # one item ≤ 60% of the original remaining budget
DEFAULT_MAX_RESULTS = MAX_BASKET_ITEMS


@dataclass(frozen=True)
class Candidate:
    """A food the user could eat, with per-100g nutrition and (when known) a serving size.
    ``food_id`` lets the diary log it by reference; list order encodes preference (recents
    first)."""

    food_id: uuid.UUID | None
    name: str
    per100_kcal: Decimal
    per100_protein_g: Decimal
    per100_fat_g: Decimal
    per100_carbs_g: Decimal
    serving_g: Decimal | None = None


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


def realistic_portion(
    *,
    target_kcal: Decimal,
    original_remaining: Decimal,
    per100_kcal: Decimal,
    serving_g: Decimal | None,
) -> Decimal:
    """A sensible portion of a food aimed at ``target_kcal`` but never more than ~60% of the
    original budget. Serving-size foods snap to whole servings (≤ MAX_SERVINGS); the rest use a
    tidy gram amount. This is what keeps protein powder at a few scoops, not half a tub."""
    cap_kcal = min(target_kcal, original_remaining * MAX_ITEM_KCAL_SHARE)
    ideal_g = cap_kcal / per100_kcal * Decimal(100)

    if serving_g is not None and serving_g > 0:
        servings = (ideal_g / serving_g).to_integral_value(rounding=ROUND_HALF_UP)
        if servings < 1:
            servings = Decimal(1)
        elif servings > MAX_SERVINGS:
            servings = Decimal(MAX_SERVINGS)
        return min(servings * serving_g, GENERIC_MAX_G)

    return min(max(_round_to_step(ideal_g), MIN_PORTION_G), GENERIC_MAX_G)


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


def suggest_basket(
    *,
    remaining_kcal: Decimal,
    protein_gap: Decimal,
    fat_gap: Decimal,
    carbs_gap: Decimal,
    candidates: list[Candidate],
    max_items: int = MAX_BASKET_ITEMS,
) -> list[Suggestion]:
    """Compose a basket of realistic portions that together fill ``remaining_kcal``.

    Greedy: at each step pick the unused food whose macro profile best matches the *residual*
    macro gap, add a realistic portion, and subtract its contribution — so the basket
    diversifies as each gap closes. Stops once the budget is essentially met, the basket is
    full, or no food can contribute meaningfully. Returns ``[]`` when the budget is already met
    (``remaining_kcal < MIN_GAP_KCAL``) or there are no usable candidates.
    """
    if remaining_kcal < MIN_GAP_KCAL:
        return []

    residual_kcal = remaining_kcal
    rp = max(protein_gap, Decimal(0))
    rf = max(fat_gap, Decimal(0))
    rc = max(carbs_gap, Decimal(0))
    # Don't chase the last few percent — a small leftover is fine and avoids over-suggesting.
    stop_kcal = max(Decimal(120), remaining_kcal * Decimal("0.08"))

    used: set[int] = set()
    basket: list[Suggestion] = []
    for _ in range(max_items):
        if residual_kcal <= stop_kcal:
            break
        gaps = (rp, rf, rc)
        best: tuple[tuple[Decimal, int], int, Candidate, Decimal] | None = None
        for idx, c in enumerate(candidates):
            if idx in used or c.per100_kcal <= 0:
                continue
            grams = realistic_portion(
                target_kcal=residual_kcal,
                original_remaining=remaining_kcal,
                per100_kcal=c.per100_kcal,
                serving_g=c.serving_g,
            )
            kcal = c.per100_kcal * grams / Decimal(100)
            if kcal < MIN_ITEM_KCAL:
                continue
            score = _cosine((c.per100_protein_g, c.per100_fat_g, c.per100_carbs_g), gaps)
            # Higher macro-fit first; round so near-ties fall back to input order (recents).
            key = (-score.quantize(Decimal("0.01")), idx)
            if best is None or key < best[0]:
                best = (key, idx, c, grams)
        if best is None:
            break

        _key, idx, c, grams = best
        used.add(idx)
        s = build_suggestion(
            food_id=c.food_id,
            name=c.name,
            amount_g=grams,
            per100_kcal=c.per100_kcal,
            per100_protein_g=c.per100_protein_g,
            per100_fat_g=c.per100_fat_g,
            per100_carbs_g=c.per100_carbs_g,
        )
        basket.append(s)
        residual_kcal -= s.kcal
        rp = max(rp - s.protein_g, Decimal(0))
        rf = max(rf - s.fat_g, Decimal(0))
        rc = max(rc - s.carbs_g, Decimal(0))

    return basket
