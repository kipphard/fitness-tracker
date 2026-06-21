"""Pure macro-target engine package (Phase 3)."""
from backend.macros.engine import (
    CARB_KCAL_PER_G,
    DEFAULT_FAT_G_PER_KG,
    DEFAULT_PROTEIN_G_PER_KG,
    FAT_KCAL_PER_G,
    FAT_MIN_G_PER_KG,
    MacroResult,
    PROTEIN_KCAL_PER_G,
    PROTEIN_RANGE_G_PER_KG,
    compute_macros,
)

__all__ = [
    "CARB_KCAL_PER_G",
    "DEFAULT_FAT_G_PER_KG",
    "DEFAULT_PROTEIN_G_PER_KG",
    "FAT_KCAL_PER_G",
    "FAT_MIN_G_PER_KG",
    "MacroResult",
    "PROTEIN_KCAL_PER_G",
    "PROTEIN_RANGE_G_PER_KG",
    "compute_macros",
]
