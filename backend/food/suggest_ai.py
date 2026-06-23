"""AI-assisted "fill the remaining calories" suggestions via Claude (issue #5, section 1).

The optional, smarter sibling of the deterministic :mod:`backend.food.suggest` engine. Given
the day's remaining kcal, macro gaps, the user's own foods, and free-text preferences, Claude
proposes a handful of foods + portions — preferring the user's catalogue but free to suggest
realistic common foods to balance macros.

Mirrors :mod:`backend.vision.estimator`: the parsing is pure and tested; the network call is
isolated in ``AnthropicSuggestClient`` and injected via a FastAPI dependency so tests
substitute a fake (no API key / no network). Returns 503 upstream until ANTHROPIC_API_KEY is
set (issue #2) — the rule-based path stays available regardless.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

import anthropic

from backend.food.suggest import Candidate

# JSON Schema for output_config.format (newer SDKs). The system prompt requests this exact
# shape too, so the result is valid JSON even on SDKs that don't accept output_config.
SUGGEST_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "suggestions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "amount_g": {"type": "number"},
                    "per100_kcal": {"type": "number"},
                    "per100_protein_g": {"type": "number"},
                    "per100_fat_g": {"type": "number"},
                    "per100_carbs_g": {"type": "number"},
                    "reason": {"type": "string"},
                },
                "required": [
                    "name",
                    "amount_g",
                    "per100_kcal",
                    "per100_protein_g",
                    "per100_fat_g",
                    "per100_carbs_g",
                    "reason",
                ],
                "additionalProperties": False,
            },
        },
        "notes": {"type": "string"},
    },
    "required": ["suggestions", "notes"],
    "additionalProperties": False,
}

SYSTEM = """You are a nutrition assistant helping a user finish their day's calorie budget. \
Given the remaining calories, the remaining macro targets (how many grams of protein/fat/carbs \
are still needed), a list of foods the user already has/eats, and optional preferences, \
suggest 3-5 single foods with realistic portions that together would help close the gap.

Prefer foods from the user's list (use their exact name and per-100g values when you do). You \
may also add common, realistic foods when they balance the macros better — especially to hit a \
protein gap.

Use REALISTIC portions: respect normal serving sizes and never suggest absurd amounts (e.g. \
not 400 g of protein powder — a scoop is ~30 g). Spread a large remaining budget across a few \
foods rather than one huge portion. Together your suggestions should roughly add up to the \
remaining calories.

Respond with ONLY a JSON object (no markdown, no prose) of exactly this shape:
{
  "suggestions": [{"name": string, "amount_g": number, "per100_kcal": number, \
"per100_protein_g": number, "per100_fat_g": number, "per100_carbs_g": number, "reason": string}],
  "notes": string
}

amount_g is the suggested portion in grams; per100_* are the food's nutrition per 100 g. \
"reason" is one short phrase (e.g. "high protein, low fat"). Keep "notes" brief. These are \
suggestions, not prescriptions. Output the JSON object only."""


@dataclass(frozen=True)
class AiSuggestion:
    name: str
    amount_g: Decimal
    per100_kcal: Decimal
    per100_protein_g: Decimal
    per100_fat_g: Decimal
    per100_carbs_g: Decimal
    reason: str


@dataclass(frozen=True)
class AiSuggestResult:
    suggestions: list[AiSuggestion]
    notes: str


def _dec(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(0)


def extract_json(text: str) -> str:
    """Pull the JSON object out of a model response (tolerates code fences / stray prose)."""
    start = text.find("{")
    end = text.rfind("}")
    return text[start : end + 1] if start != -1 and end != -1 else text


def parse_suggestions(payload: dict) -> AiSuggestResult:
    """Build an AiSuggestResult from the decoded JSON dict. Missing fields degrade gracefully;
    items without a positive portion or energy are dropped (they can't be logged)."""
    suggestions: list[AiSuggestion] = []
    for it in payload.get("suggestions", []):
        amount = _dec(it.get("amount_g"))
        per100_kcal = _dec(it.get("per100_kcal"))
        if amount <= 0 or per100_kcal <= 0:
            continue
        suggestions.append(
            AiSuggestion(
                name=str(it.get("name", "")).strip()[:200] or "food",
                amount_g=amount,
                per100_kcal=per100_kcal,
                per100_protein_g=_dec(it.get("per100_protein_g")),
                per100_fat_g=_dec(it.get("per100_fat_g")),
                per100_carbs_g=_dec(it.get("per100_carbs_g")),
                reason=str(it.get("reason", "")).strip()[:200],
            )
        )
    return AiSuggestResult(
        suggestions=suggestions,
        notes=str(payload.get("notes", "")).strip(),
    )


def _format_candidates(candidates: list[Candidate], limit: int = 40) -> str:
    if not candidates:
        return "(none yet)"
    lines = []
    for c in candidates[:limit]:
        serving = f", serving {c.serving_g} g" if c.serving_g else ""
        lines.append(
            f"- {c.name} (per 100 g: {c.per100_kcal} kcal, "
            f"{c.per100_protein_g} P / {c.per100_fat_g} F / {c.per100_carbs_g} C{serving})"
        )
    return "\n".join(lines)


# --- full-day meal plan (issue #5, section 2) ---

VALID_SLOTS = ("breakfast", "lunch", "dinner", "snack")

# JSON Schema for the day plan: meals (each a slot + a few items) plus brief notes. Emitted via
# output_config on newer SDKs; the PLAN_SYSTEM prompt requests the same shape as a fallback.
PLAN_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "meals": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "slot": {"type": "string", "enum": list(VALID_SLOTS)},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "amount_g": {"type": "number"},
                                "per100_kcal": {"type": "number"},
                                "per100_protein_g": {"type": "number"},
                                "per100_fat_g": {"type": "number"},
                                "per100_carbs_g": {"type": "number"},
                                "reason": {"type": "string"},
                            },
                            "required": [
                                "name",
                                "amount_g",
                                "per100_kcal",
                                "per100_protein_g",
                                "per100_fat_g",
                                "per100_carbs_g",
                                "reason",
                            ],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["slot", "items"],
                "additionalProperties": False,
            },
        },
        "notes": {"type": "string"},
    },
    "required": ["meals", "notes"],
    "additionalProperties": False,
}

PLAN_SYSTEM = """You are a nutrition assistant building a realistic day of meals for a user. \
Given a calorie + macro target (protein/fat/carbs in grams), the number of meals to plan, the \
user's country and store, their dietary preferences, and a list of foods they already \
have/eat, produce a meal plan whose portions TOGETHER roughly hit the targets.

Plan exactly the requested number of meals using the standard slots in order \
(breakfast, lunch, dinner, then snack if a 4th meal). Each meal has 1-3 food items.

Constrain every item to a REALISTIC product the user can actually buy in their country and \
store (use concrete, common product names). Prefer foods from the user's list (use their exact \
name and per-100g values when you do). Respect dietary preferences strictly. Use realistic \
portions and normal serving sizes — never absurd amounts.

Respond with ONLY a JSON object (no markdown, no prose) of exactly this shape:
{
  "meals": [{"slot": "breakfast"|"lunch"|"dinner"|"snack", "items": [{"name": string, \
"amount_g": number, "per100_kcal": number, "per100_protein_g": number, "per100_fat_g": number, \
"per100_carbs_g": number, "reason": string}]}],
  "notes": string
}

amount_g is the portion in grams; per100_* are the food's nutrition per 100 g. "reason" is one \
short phrase. Keep "notes" brief. These are suggestions, not prescriptions. Output the JSON \
object only."""


@dataclass(frozen=True)
class AiPlanItem:
    name: str
    amount_g: Decimal
    per100_kcal: Decimal
    per100_protein_g: Decimal
    per100_fat_g: Decimal
    per100_carbs_g: Decimal
    reason: str


@dataclass(frozen=True)
class AiPlanMeal:
    slot: str
    items: list[AiPlanItem]


@dataclass(frozen=True)
class AiDayPlan:
    meals: list[AiPlanMeal]
    notes: str


def parse_plan(payload: dict) -> AiDayPlan:
    """Build an AiDayPlan from the decoded JSON dict. Unknown slots and zero-portion/zero-energy
    items are dropped; meals left with no usable items are omitted entirely."""
    meals: list[AiPlanMeal] = []
    for m in payload.get("meals", []):
        slot = str(m.get("slot", "")).strip().lower()
        if slot not in VALID_SLOTS:
            continue
        items: list[AiPlanItem] = []
        for it in m.get("items", []):
            amount = _dec(it.get("amount_g"))
            per100_kcal = _dec(it.get("per100_kcal"))
            if amount <= 0 or per100_kcal <= 0:
                continue
            items.append(
                AiPlanItem(
                    name=str(it.get("name", "")).strip()[:200] or "food",
                    amount_g=amount,
                    per100_kcal=per100_kcal,
                    per100_protein_g=_dec(it.get("per100_protein_g")),
                    per100_fat_g=_dec(it.get("per100_fat_g")),
                    per100_carbs_g=_dec(it.get("per100_carbs_g")),
                    reason=str(it.get("reason", "")).strip()[:200],
                )
            )
        if items:
            meals.append(AiPlanMeal(slot=slot, items=items))
    return AiDayPlan(meals=meals, notes=str(payload.get("notes", "")).strip())


class AnthropicSuggestClient:
    """Wraps a Claude suggestion call. Injected via ``get_suggest_client``; faked in tests."""

    def __init__(self, api_key: str, model: str) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def suggest(
        self,
        *,
        remaining_kcal: Decimal,
        protein_gap: Decimal,
        fat_gap: Decimal,
        carbs_gap: Decimal,
        candidates: list[Candidate],
        preferences: str | None = None,
    ) -> AiSuggestResult:
        user_text = (
            f"Remaining for today: {remaining_kcal} kcal.\n"
            f"Macros still needed: {protein_gap} g protein, {fat_gap} g fat, "
            f"{carbs_gap} g carbs.\n\n"
            f"Foods the user has/eats:\n{_format_candidates(candidates)}\n"
        )
        if preferences and preferences.strip():
            user_text += f"\nUser preferences: {preferences.strip()}\n"
        user_text += "\nSuggest foods and portions to fill the remaining calories."

        kwargs: dict = {
            "model": self._model,
            "max_tokens": 2048,
            "system": SYSTEM,
            "messages": [{"role": "user", "content": user_text}],
        }
        try:
            resp = self._client.messages.create(
                **kwargs,
                output_config={"format": {"type": "json_schema", "schema": SUGGEST_SCHEMA}},
            )
        except TypeError:
            # Older SDK without output_config — the system prompt still yields JSON.
            resp = self._client.messages.create(**kwargs)

        text = next((b.text for b in resp.content if getattr(b, "type", None) == "text"), "")
        return parse_suggestions(json.loads(extract_json(text)))

    def plan(
        self,
        *,
        scope: str,
        kcal_budget: Decimal,
        protein_target: Decimal,
        fat_target: Decimal,
        carbs_target: Decimal,
        meals: int,
        candidates: list[Candidate],
        country: str | None = None,
        store: str | None = None,
        dietary_preferences: str | None = None,
        preferences: str | None = None,
    ) -> AiDayPlan:
        horizon = "the whole day" if scope == "full_day" else "the rest of the day"
        user_text = (
            f"Plan {meals} meals for {horizon}.\n"
            f"Targets to hit together: {kcal_budget} kcal, {protein_target} g protein, "
            f"{fat_target} g fat, {carbs_target} g carbs.\n\n"
            f"Foods the user already has/eats:\n{_format_candidates(candidates)}\n"
        )
        context = [
            (f"Country: {country.strip()}" if country and country.strip() else None),
            (f"Store: {store.strip()}" if store and store.strip() else None),
            (
                f"Dietary preferences: {dietary_preferences.strip()}"
                if dietary_preferences and dietary_preferences.strip()
                else None
            ),
            (f"Extra notes: {preferences.strip()}" if preferences and preferences.strip() else None),
        ]
        for line in context:
            if line:
                user_text += f"\n{line}"
        user_text += "\n\nBuild the meal plan."

        kwargs: dict = {
            "model": self._model,
            "max_tokens": 3072,
            "system": PLAN_SYSTEM,
            "messages": [{"role": "user", "content": user_text}],
        }
        try:
            resp = self._client.messages.create(
                **kwargs,
                output_config={"format": {"type": "json_schema", "schema": PLAN_SCHEMA}},
            )
        except TypeError:
            # Older SDK without output_config — the system prompt still yields JSON.
            resp = self._client.messages.create(**kwargs)

        text = next((b.text for b in resp.content if getattr(b, "type", None) == "text"), "")
        return parse_plan(json.loads(extract_json(text)))
