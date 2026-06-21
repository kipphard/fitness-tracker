"""Photo meal estimation via Claude vision (Phase 5).

Sends a meal photo (and optional user notes) to a Claude vision model and returns a structured
estimate of the food items + macros, plus clarifying questions when the photo is ambiguous.

The estimate is *approximate* — a fast-entry aid, not a scale. The parsing is pure and tested;
the network call is isolated in ``AnthropicVisionClient`` and injected via a FastAPI dependency
so tests substitute a fake (no API key / no network).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

import anthropic

# JSON Schema for output_config.format (newer SDKs). The system prompt also requests this exact
# shape, so the result is valid JSON even on SDKs that don't accept output_config.
ESTIMATE_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "amount_g": {"type": "number"},
                    "kcal": {"type": "number"},
                    "protein_g": {"type": "number"},
                    "fat_g": {"type": "number"},
                    "carbs_g": {"type": "number"},
                },
                "required": ["name", "amount_g", "kcal", "protein_g", "fat_g", "carbs_g"],
                "additionalProperties": False,
            },
        },
        "total": {
            "type": "object",
            "properties": {
                "kcal": {"type": "number"},
                "protein_g": {"type": "number"},
                "fat_g": {"type": "number"},
                "carbs_g": {"type": "number"},
            },
            "required": ["kcal", "protein_g", "fat_g", "carbs_g"],
            "additionalProperties": False,
        },
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
        "questions": {"type": "array", "items": {"type": "string"}},
        "notes": {"type": "string"},
    },
    "required": ["items", "total", "confidence", "questions", "notes"],
    "additionalProperties": False,
}

SYSTEM = """You are a nutrition estimation assistant. Given a photo of a meal (plus optional \
notes from the user), estimate each food item and its nutrition.

Respond with ONLY a JSON object (no markdown, no prose) of exactly this shape:
{
  "items": [{"name": string, "amount_g": number, "kcal": number, "protein_g": number, \
"fat_g": number, "carbs_g": number}],
  "total": {"kcal": number, "protein_g": number, "fat_g": number, "carbs_g": number},
  "confidence": "low" | "medium" | "high",
  "questions": [string],
  "notes": string
}

amount_g is the estimated portion in grams; kcal/protein_g/fat_g/carbs_g are for that portion. \
"total" sums all items. Use realistic typical portions. When the photo is ambiguous (portion \
size, oil/butter, hidden ingredients, cooking method), add up to 3 short "questions" the user \
could answer to improve accuracy; use an empty array when confident. Estimates are approximate \
— keep "notes" brief. Output the JSON object only."""


@dataclass(frozen=True)
class EstimateItem:
    name: str
    amount_g: Decimal
    kcal: Decimal
    protein_g: Decimal
    fat_g: Decimal
    carbs_g: Decimal


@dataclass(frozen=True)
class MacroTotal:
    kcal: Decimal
    protein_g: Decimal
    fat_g: Decimal
    carbs_g: Decimal


@dataclass(frozen=True)
class PhotoEstimate:
    items: list[EstimateItem]
    total: MacroTotal
    confidence: str
    questions: list[str]
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


def parse_estimate(payload: dict) -> PhotoEstimate:
    """Build a PhotoEstimate from the decoded JSON dict. Missing fields degrade gracefully."""
    items = [
        EstimateItem(
            name=str(it.get("name", "")).strip()[:200] or "item",
            amount_g=_dec(it.get("amount_g")),
            kcal=_dec(it.get("kcal")),
            protein_g=_dec(it.get("protein_g")),
            fat_g=_dec(it.get("fat_g")),
            carbs_g=_dec(it.get("carbs_g")),
        )
        for it in payload.get("items", [])
    ]
    total_raw = payload.get("total") or {}
    total = MacroTotal(
        kcal=_dec(total_raw.get("kcal")),
        protein_g=_dec(total_raw.get("protein_g")),
        fat_g=_dec(total_raw.get("fat_g")),
        carbs_g=_dec(total_raw.get("carbs_g")),
    )
    confidence = str(payload.get("confidence", "low")).lower()
    if confidence not in {"low", "medium", "high"}:
        confidence = "low"
    questions = [str(q).strip() for q in payload.get("questions", []) if str(q).strip()][:3]
    return PhotoEstimate(
        items=items,
        total=total,
        confidence=confidence,
        questions=questions,
        notes=str(payload.get("notes", "")).strip(),
    )


class AnthropicVisionClient:
    """Wraps a Claude vision call. Injected via ``get_vision_client``; faked in tests."""

    def __init__(self, api_key: str, model: str) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def estimate(
        self, *, image_b64: str, media_type: str, context: str | None = None
    ) -> PhotoEstimate:
        user_text = (
            "Estimate this meal."
            if not context
            else f"The user adds these details: {context}\nUpdate your estimate accordingly."
        )
        content = [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": media_type, "data": image_b64},
            },
            {"type": "text", "text": user_text},
        ]
        kwargs: dict = {
            "model": self._model,
            "max_tokens": 2048,
            "system": SYSTEM,
            "messages": [{"role": "user", "content": content}],
        }
        try:
            resp = self._client.messages.create(
                **kwargs,
                output_config={"format": {"type": "json_schema", "schema": ESTIMATE_SCHEMA}},
            )
        except TypeError:
            # Older SDK without output_config — the system prompt still yields JSON.
            resp = self._client.messages.create(**kwargs)

        text = next((b.text for b in resp.content if getattr(b, "type", None) == "text"), "")
        return parse_estimate(json.loads(extract_json(text)))
