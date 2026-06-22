"""Pure workout → calorie estimation (issue #3).

MET-based: ``kcal = MET × weight(kg) × hours``. Strength training sits around 3.5 (light) to
6.0 (vigorous) MET; we default to 5.0. Duration is estimated from set count (~3.5 min per set,
including rest) — the reliable signal for lifting. Recorded wall-clock (``started_at →
ended_at``) is used only when it's *longer* than that estimate: it's frequently implausibly
short (all sets tapped in quickly, or a past workout backfilled), so it must never drag the burn
below the set-count floor. An empty session (no sets) burns nothing; a manual ``kcal_override``
short-circuits everything.

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
    """Workout hours, capped at MAX_HOURS.

    The set-count estimate (~MIN_PER_SET each, incl. rest) is the floor. Recorded wall-clock is
    used only when it's longer — a too-short recorded time (fast logging / backfill) never lowers
    the burn below what the logged sets imply.
    """
    hours = _dec(set_count) * MIN_PER_SET / Decimal(60)
    if started_at is not None and ended_at is not None and ended_at > started_at:
        measured = _dec(str((ended_at - started_at).total_seconds())) / Decimal(3600)
        hours = max(measured, hours)
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
    if set_count <= 0:  # a session started then abandoned (no sets logged) burns nothing
        return Decimal(0)
    return _dec(met) * _dec(weight_kg) * _duration_hours(started_at, ended_at, set_count)
