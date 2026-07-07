"""Pure parsing of the Claude nutrition-label response."""
from decimal import Decimal

from backend.vision.label import parse_label


def test_parse_label_builds_draft():
    draft = parse_label(
        {
            "name": "Skyr Vanilla",
            "per100_kcal": 74,
            "per100_protein_g": 10,
            "per100_fat_g": 0.2,
            "per100_carbs_g": 7.5,
            "serving_g": 150,
        }
    )
    assert draft.name == "Skyr Vanilla"
    assert draft.per100_kcal == Decimal("74")
    assert draft.per100_fat_g == Decimal("0.2")
    assert draft.serving_g == Decimal("150")


def test_parse_label_degrades_gracefully():
    draft = parse_label({})
    assert draft.name == ""
    assert draft.per100_kcal == Decimal("0")
    assert draft.serving_g is None


def test_parse_label_clamps_to_foodin_ranges():
    draft = parse_label(
        {
            "name": "x" * 500,
            "per100_kcal": 9999,  # > 1000 cap
            "per100_protein_g": 250,  # > 100 cap
            "per100_fat_g": -5,  # < 0 floor
            "per100_carbs_g": 7,
            "serving_g": 99999,  # > 5000 cap
        }
    )
    assert len(draft.name) == 200
    assert draft.per100_kcal == Decimal("1000")
    assert draft.per100_protein_g == Decimal("100")
    assert draft.per100_fat_g == Decimal("0")
    assert draft.serving_g == Decimal("5000")


def test_parse_label_zero_or_negative_serving_is_none():
    assert parse_label({"serving_g": 0}).serving_g is None
    assert parse_label({"serving_g": -3}).serving_g is None
