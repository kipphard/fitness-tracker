"""Nutrition-label (Nährwerttabelle) reader via Claude vision.

Given a photo of a packaged food's nutrition-facts table, extract the per-100g values so the
user can create a food from them. Distinct from ``estimator`` (meal photos): a label lists
per-100g values directly, so there is no portion math — the output maps straight onto Food's
``per100_*`` fields.

The parsing is pure and tested; the network call is isolated in ``AnthropicLabelClient`` and
injected via a FastAPI dependency so tests substitute a fake (no API key / no network).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

import anthropic

from backend.vision.estimator import extract_json

# JSON Schema for output_config.format (newer SDKs). The system prompt requests the same shape,
# so the result is valid JSON even on SDKs that don't accept output_config.
LABEL_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "per100_kcal": {"type": "number"},
        "per100_protein_g": {"type": "number"},
        "per100_fat_g": {"type": "number"},
        "per100_carbs_g": {"type": "number"},
        "serving_g": {"type": ["number", "null"]},
    },
    "required": [
        "name",
        "per100_kcal",
        "per100_protein_g",
        "per100_fat_g",
        "per100_carbs_g",
        "serving_g",
    ],
    "additionalProperties": False,
}

SYSTEM = """You read nutrition-facts tables (Nährwerttabelle) from a photo of a food package \
and return the nutrition per 100 g.

Respond with ONLY a JSON object (no markdown, no prose) of exactly this shape:
{
  "name": string,
  "per100_kcal": number,
  "per100_protein_g": number,
  "per100_fat_g": number,
  "per100_carbs_g": number,
  "serving_g": number | null
}

All macro values are per 100 g (or per 100 ml for drinks). If the label lists values only per \
serving, convert them to per 100 g using the stated serving size. Energy is in kcal — if only \
kJ is shown, convert (kcal = kJ / 4.184). "name" is the product name if visible on the package, \
else an empty string. "serving_g" is the stated serving/portion size in grams if present, else \
null. If a value is not legible, use 0. Output the JSON object only."""


@dataclass(frozen=True)
class FoodLabelDraft:
    name: str
    per100_kcal: Decimal
    per100_protein_g: Decimal
    per100_fat_g: Decimal
    per100_carbs_g: Decimal
    serving_g: Decimal | None


def _dec(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(0)


def _clamp(value: Decimal, lo: Decimal, hi: Decimal) -> Decimal:
    return max(lo, min(hi, value))


def _serving(value: Any) -> Decimal | None:
    """Serving size in grams, or None. Clamped to the FoodIn range (0 < g <= 5000)."""
    if value is None or value == "":
        return None
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    if d <= 0:
        return None
    return min(d, Decimal(5000))


def parse_label(payload: dict) -> FoodLabelDraft:
    """Build a FoodLabelDraft from the decoded JSON, clamped to the FoodIn field ranges so the
    prefilled custom-food form always validates. Missing fields degrade to 0 / None."""
    return FoodLabelDraft(
        name=str(payload.get("name", "")).strip()[:200],
        per100_kcal=_clamp(_dec(payload.get("per100_kcal")), Decimal(0), Decimal(1000)),
        per100_protein_g=_clamp(_dec(payload.get("per100_protein_g")), Decimal(0), Decimal(100)),
        per100_fat_g=_clamp(_dec(payload.get("per100_fat_g")), Decimal(0), Decimal(100)),
        per100_carbs_g=_clamp(_dec(payload.get("per100_carbs_g")), Decimal(0), Decimal(100)),
        serving_g=_serving(payload.get("serving_g")),
    )


class AnthropicLabelClient:
    """Wraps a Claude vision call to read a nutrition label. Injected via ``get_label_client``."""

    def __init__(self, api_key: str, model: str) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def read_label(self, *, image_b64: str, media_type: str) -> FoodLabelDraft:
        content = [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": media_type, "data": image_b64},
            },
            {"type": "text", "text": "Read this nutrition-facts table."},
        ]
        kwargs: dict = {
            "model": self._model,
            "max_tokens": 1024,
            "system": SYSTEM,
            "messages": [{"role": "user", "content": content}],
        }
        try:
            resp = self._client.messages.create(
                **kwargs,
                output_config={"format": {"type": "json_schema", "schema": LABEL_SCHEMA}},
            )
        except TypeError:
            # Older SDK without output_config — the system prompt still yields JSON.
            resp = self._client.messages.create(**kwargs)

        text = next((b.text for b in resp.content if getattr(b, "type", None) == "text"), "")
        return parse_label(json.loads(extract_json(text)))
