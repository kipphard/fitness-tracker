"""Pure macro-target engine (Phase 3).

Protein and fat are set per kilogram of bodyweight; carbohydrates fill whatever calories
remain in the daily target. The split must reconcile to the calorie target:

    protein_g*4 + carbs_g*4 + fat_g*9 = target_kcal

If protein + fat alone already exceed the target, carbs clamp to 0 and the result is flagged
as not reconciled (the caller surfaces a warning).

Pure: no database, no framework. All values are :class:`~decimal.Decimal`, never ``float``.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

PROTEIN_KCAL_PER_G = Decimal(4)
CARB_KCAL_PER_G = Decimal(4)
FAT_KCAL_PER_G = Decimal(9)

# Auto-suggest defaults (within the commonly recommended ranges).
DEFAULT_PROTEIN_G_PER_KG = Decimal("2.0")
DEFAULT_FAT_G_PER_KG = Decimal("0.8")

# Guidance for the UI / sanity bounds.
PROTEIN_RANGE_G_PER_KG = (Decimal("1.6"), Decimal("2.2"))
FAT_MIN_G_PER_KG = Decimal("0.6")


@dataclass(frozen=True)
class MacroResult:
    protein_g: Decimal
    fat_g: Decimal
    carbs_g: Decimal
    protein_kcal: Decimal
    fat_kcal: Decimal
    carbs_kcal: Decimal
    target_kcal: Decimal
    reconciled: bool
    over_kcal: Decimal  # by how much protein+fat exceed the target (0 when reconciled)


def _dec(value: Decimal | int | float | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal(value)


def compute_macros(
    target_kcal: Decimal | int | float | str,
    weight_kg: Decimal | int | float | str,
    protein_g_per_kg: Decimal | int | float | str = DEFAULT_PROTEIN_G_PER_KG,
    fat_g_per_kg: Decimal | int | float | str = DEFAULT_FAT_G_PER_KG,
) -> MacroResult:
    target = _dec(target_kcal)
    weight = _dec(weight_kg)

    protein_g = weight * _dec(protein_g_per_kg)
    fat_g = weight * _dec(fat_g_per_kg)
    protein_kcal = protein_g * PROTEIN_KCAL_PER_G
    fat_kcal = fat_g * FAT_KCAL_PER_G

    remaining = target - protein_kcal - fat_kcal
    if remaining < 0:
        return MacroResult(
            protein_g=protein_g,
            fat_g=fat_g,
            carbs_g=Decimal(0),
            protein_kcal=protein_kcal,
            fat_kcal=fat_kcal,
            carbs_kcal=Decimal(0),
            target_kcal=target,
            reconciled=False,
            over_kcal=-remaining,
        )
    return MacroResult(
        protein_g=protein_g,
        fat_g=fat_g,
        carbs_g=remaining / CARB_KCAL_PER_G,
        protein_kcal=protein_kcal,
        fat_kcal=fat_kcal,
        carbs_kcal=remaining,
        target_kcal=target,
        reconciled=True,
        over_kcal=Decimal(0),
    )
