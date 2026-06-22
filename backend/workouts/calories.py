"""Pure workout → calorie estimation (issue #3).

MET-based: ``kcal = MET × weight(kg) × hours``. Strength training sits around 3.5 (light) to
6.0 (vigorous) MET; we default to 5.0. Duration comes from ``started_at → ended_at``; sessions
the user never "finished" have no end time, so we fall back to a rough estimate from set count
(~3.5 min per set, including rest). A manual ``kcal_override`` short-circuits everything.

Like step burn, this is a first-order estimate — the adaptive-TDEE correction (issue #4) absorbs
the systematic error. No I/O; Decimal only.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

# General resistance training, multiple exercises — between light (3.5) and vigorous (6.0) MET.
DEFAULT_MET = Decimal("5.0")
# Fallback when a session was never finished: assume each logged set + rest takes this long.
MIN_PER_SET = Decimal("3.5")
# Cap duration so a session left open for hours (forgot to hit finish) can't inflate the burn.
MAX_HOURS = Decimal("3")


def _dec(value: Decimal | int | float | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal(value)


def _duration_hours(
    started_at: datetime | None, ended_at: datetime | None, set_count: int
) -> Decimal:
    """Workout hours: measured (started→ended) if finished, else estimated from set count."""
    if started_at is not None and ended_at is not None and ended_at > started_at:
        hours = _dec(str((ended_at - started_at).total_seconds())) / Decimal(3600)
    else:
        hours = _dec(set_count) * MIN_PER_SET / Decimal(60)
    return min(hours, MAX_HOURS)


def session_kcal(
    weight_kg: Decimal | int | float | str,
    *,
    started_at: datetime | None,
    ended_at: datetime | None,
    set_count: int,
    met: Decimal | int | float | str = DEFAULT_MET,
    kcal_override: Decimal | int | float | str | None = None,
) -> Decimal:
    """Calories burned in one workout session."""
    if kcal_override is not None:
        return _dec(kcal_override)
    return _dec(met) * _dec(weight_kg) * _duration_hours(started_at, ended_at, set_count)
