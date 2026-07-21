"""Pure step → calorie conversion (Phase 6).

kcal ≈ steps × 0.0005 × weight(kg). A rough estimate (e.g. 10k steps @ 95 kg ≈ 475 kcal).
No I/O; Decimal only.
"""
from __future__ import annotations

from decimal import Decimal

STEP_KCAL_FACTOR = Decimal("0.0005")


def _dec(value: Decimal | int | float | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal(value)


def steps_to_kcal(steps: int, weight_kg: Decimal | int | float | str) -> Decimal:
    """Calories burned walking `steps` at body weight `weight_kg`."""
    return _dec(steps) * STEP_KCAL_FACTOR * _dec(weight_kg)
