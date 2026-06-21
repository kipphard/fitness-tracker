"""Pure portion scaling: per-100g nutrition × grams logged.

No I/O. All values are :class:`~decimal.Decimal`, never ``float``.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


def _dec(value: Decimal | int | float | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal(value)


@dataclass(frozen=True)
class ScaledMacros:
    kcal: Decimal
    protein_g: Decimal
    fat_g: Decimal
    carbs_g: Decimal


def scale_per100(
    *,
    per100_kcal: Decimal | int | float | str,
    per100_protein_g: Decimal | int | float | str,
    per100_fat_g: Decimal | int | float | str,
    per100_carbs_g: Decimal | int | float | str,
    amount_g: Decimal | int | float | str,
) -> ScaledMacros:
    factor = _dec(amount_g) / Decimal(100)
    return ScaledMacros(
        kcal=_dec(per100_kcal) * factor,
        protein_g=_dec(per100_protein_g) * factor,
        fat_g=_dec(per100_fat_g) * factor,
        carbs_g=_dec(per100_carbs_g) * factor,
    )
