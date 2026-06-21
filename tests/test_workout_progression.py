"""Pure workout progression math."""
from decimal import Decimal

from backend.workouts.progression import epley_1rm, set_volume


def test_epley_1rm():
    assert epley_1rm(100, 3) == Decimal("110.0")  # 100 * (1 + 3/30)
    assert epley_1rm(60, 10) == Decimal("80.0")  # 60 * (4/3)
    assert epley_1rm(80, 1) == Decimal("80.0")  # 1 rep -> the weight
    assert epley_1rm(100, 0) == Decimal("100.0")


def test_set_volume():
    assert set_volume(100, 5) == Decimal("500")
    assert set_volume(Decimal("62.5"), 8) == Decimal("500.0")
