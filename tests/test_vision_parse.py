"""Pure parsing of the Claude vision estimate response."""
from decimal import Decimal

from backend.vision.estimator import extract_json, parse_estimate


def test_extract_json_strips_fences_and_prose():
    raw = 'Here you go:\n```json\n{"a": 1}\n```'
    assert extract_json(raw) == '{"a": 1}'


def test_parse_estimate_builds_items_and_total():
    payload = {
        "items": [
            {"name": "Rice", "amount_g": 150, "kcal": 195, "protein_g": 4, "fat_g": 0.4, "carbs_g": 43}
        ],
        "total": {"kcal": 195, "protein_g": 4, "fat_g": 0.4, "carbs_g": 43},
        "confidence": "medium",
        "questions": ["Any sauce?"],
        "notes": "ok",
    }
    e = parse_estimate(payload)
    assert len(e.items) == 1
    assert e.items[0].name == "Rice"
    assert e.items[0].amount_g == Decimal("150")
    assert e.items[0].fat_g == Decimal("0.4")
    assert e.total.kcal == Decimal("195")
    assert e.confidence == "medium"
    assert e.questions == ["Any sauce?"]


def test_parse_estimate_degrades_gracefully():
    e = parse_estimate({})
    assert e.items == []
    assert e.confidence == "low"
    assert e.total.kcal == Decimal("0")


def test_parse_estimate_clamps_confidence_and_questions():
    e = parse_estimate({"confidence": "really-sure", "questions": ["a", "b", "c", "d"]})
    assert e.confidence == "low"  # unknown value falls back
    assert len(e.questions) == 3  # capped at 3
