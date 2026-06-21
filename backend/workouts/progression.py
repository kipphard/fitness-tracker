"""Pure workout progression math (Phase 7).

Estimated 1RM via Epley, and set volume. No I/O; Decimal only.
"""
from __future__ import annotations

from decimal import Decimal

_TENTH = Decimal("0.1")


def _dec(value: Decimal | int | float | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal(value)


def epley_1rm(weight: Decimal | int | float | str, reps: int) -> Decimal:
    """Estimated one-rep max (Epley): weight × (1 + reps/30). 1 rep → the weight itself."""
    r = int(reps)
    w = _dec(weight)
    if r <= 1:
        return w.quantize(_TENTH)
    return (w * (Decimal(1) + Decimal(r) / Decimal(30))).quantize(_TENTH)


def set_volume(weight: Decimal | int | float | str, reps: int) -> Decimal:
    """Volume of a single set: weight × reps."""
    return _dec(weight) * Decimal(int(reps))
