"""Pure weight-trend module (Phase 2).

Turns daily weigh-ins into weekly averages and an EWMA "trend weight" (which smooths out
daily water-weight noise), and picks the *effective weight* that feeds the calorie target:
the last completed week's average — your weekly-average instinct, made concrete.

Pure: no database, no framework. All values are :class:`~decimal.Decimal`, never ``float``.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum

# Smoothing factor for the trend weight. ~0.1 ≈ a week of memory: daily fluctuations are
# damped while real changes still come through.
EWMA_ALPHA = Decimal("0.1")


class WeightSource(str, Enum):
    """Where the weight feeding the calorie target came from."""

    weekly_average = "weekly_average"
    latest_weigh_in = "latest_weigh_in"
    profile = "profile"


@dataclass(frozen=True)
class WeekAverage:
    week_start: date  # Monday of the ISO week
    average: Decimal
    count: int


@dataclass(frozen=True)
class TrendPoint:
    date: date
    trend: Decimal


Point = tuple[date, Decimal | int | float | str]


def _dec(value: Decimal | int | float | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal(value)


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def weekly_averages(points: list[Point]) -> list[WeekAverage]:
    """Mean weight per ISO week (weeks with no weigh-ins are omitted), oldest first."""
    groups: dict[date, list[Decimal]] = {}
    for d, w in points:
        groups.setdefault(_monday(d), []).append(_dec(w))
    out: list[WeekAverage] = []
    for week_start in sorted(groups):
        weights = groups[week_start]
        avg = sum(weights, Decimal(0)) / Decimal(len(weights))
        out.append(WeekAverage(week_start=week_start, average=avg, count=len(weights)))
    return out


def ewma_trend(points: list[Point], alpha: Decimal = EWMA_ALPHA) -> list[TrendPoint]:
    """Exponentially weighted moving average over the date-ordered weigh-ins."""
    a = _dec(alpha)
    ordered = sorted(points, key=lambda p: p[0])
    out: list[TrendPoint] = []
    prev: Decimal | None = None
    for d, w in ordered:
        weight = _dec(w)
        prev = weight if prev is None else a * weight + (Decimal(1) - a) * prev
        out.append(TrendPoint(date=d, trend=prev))
    return out


def last_completed_week_average(points: list[Point], today: date) -> Decimal | None:
    """Average of the most recent data-bearing ISO week that has fully elapsed."""
    current_monday = _monday(today)
    completed = [wa for wa in weekly_averages(points) if wa.week_start < current_monday]
    return completed[-1].average if completed else None


def latest_weight(points: list[Point]) -> Decimal | None:
    if not points:
        return None
    return _dec(max(points, key=lambda p: p[0])[1])


def weekly_change(points: list[Point], today: date) -> Decimal | None:
    """Change between the two most recent completed weeks (latest − previous). Negative is a
    loss. None if fewer than two completed, data-bearing weeks exist (Phase 8 rate guardrail)."""
    current_monday = _monday(today)
    completed = [wa for wa in weekly_averages(points) if wa.week_start < current_monday]
    if len(completed) < 2:
        return None
    return completed[-1].average - completed[-2].average


def effective_weight(
    points: list[Point], today: date, fallback: Decimal | int | float | str
) -> tuple[Decimal, WeightSource]:
    """The weight that feeds the calorie target.

    Prefers the last completed week's average; falls back to the latest weigh-in, then to the
    supplied profile weight.
    """
    week_avg = last_completed_week_average(points, today)
    if week_avg is not None:
        return week_avg, WeightSource.weekly_average
    latest = latest_weight(points)
    if latest is not None:
        return latest, WeightSource.latest_weigh_in
    return _dec(fallback), WeightSource.profile
