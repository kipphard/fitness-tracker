"""Macro-engine unit tests — the protein/fat/carbs split and the over-target guardrail."""
from decimal import Decimal

from backend.macros.engine import compute_macros


def test_macro_split_reconciles():
    r = compute_macros(
        target_kcal=Decimal("2000"),
        weight_kg=Decimal("80"),
        protein_g_per_kg=Decimal("2.0"),
        fat_g_per_kg=Decimal("0.8"),
    )
    assert r.protein_g == Decimal("160")  # 80 * 2.0
    assert r.fat_g == Decimal("64")  # 80 * 0.8
    assert r.protein_kcal == Decimal("640")  # 160 * 4
    assert r.fat_kcal == Decimal("576")  # 64 * 9
    assert r.carbs_kcal == Decimal("784")  # 2000 - 640 - 576
    assert r.carbs_g == Decimal("196")  # 784 / 4
    assert r.reconciled is True
    assert r.over_kcal == Decimal("0")


def test_defaults_used_when_not_specified():
    r = compute_macros(Decimal("2000"), Decimal("80"))
    assert r.protein_g == Decimal("160")  # default 2.0 g/kg
    assert r.fat_g == Decimal("64")  # default 0.8 g/kg


def test_over_target_clamps_carbs_and_flags():
    # 100 kg: protein 200 g (800 kcal) + fat 80 g (720 kcal) = 1520 > 1200.
    r = compute_macros(Decimal("1200"), Decimal("100"), Decimal("2.0"), Decimal("0.8"))
    assert r.carbs_g == Decimal("0")
    assert r.carbs_kcal == Decimal("0")
    assert r.reconciled is False
    assert r.over_kcal == Decimal("320")  # 1520 - 1200
