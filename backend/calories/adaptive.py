"""Adaptive TDEE — learn true maintenance from intake vs. weight change (issue #4, master §5.2).

The formula maintenance (Mifflin × activity) is a population estimate; an individual's real
maintenance can sit ±15–20% off it. Energy balance lets us *measure* it: if you average
``I`` kcal/day and your trend weight changes by ``Δ`` kg over ``D`` days, then

    measured_TDEE ≈ I − (Δ × 7700) / D            (7700 kcal ≈ 1 kg of body mass)

We estimate ``Δ/D`` (kg/day) with a least-squares slope over the window's weigh-ins rather
than EWMA endpoints — EWMA lags and under-reports the change when weigh-ins are sparse or
irregular, whereas the slope is robust and uses every point.

``measured_TDEE`` from energy balance is *total* expenditure — it includes deliberate exercise.
The formula maintenance is BMR × an occupational factor (e.g. ×1.2 for a desk job), so it already
grants an everyday-activity allowance but excludes deliberate exercise. To keep ``measured``
comparable to the formula, we subtract only the window's mean activity **above that occupational
allowance** (``activity_floor`` = formula − BMR, derived from the user's activity-level setting) —
i.e. the deliberate exercise / extra movement the formula doesn't cover, leaving everyday activity
in the baseline. Once enough dense data exists we blend that baseline into the formula, with
confidence growing as the window fills, so the target self-corrects per person. Below the data
threshold confidence is 0 → pure formula.

Pure: no database, no framework. All values are :class:`~decimal.Decimal`, never ``float``.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

KCAL_PER_KG = Decimal("7700")  # Wishnofsky's ~3500 kcal/lb; a first-order conversion.

WINDOW_DAYS = 28  # Trailing window we measure over — long enough for signal, short enough to
# stay current as weight (and thus maintenance) drifts.
MIN_SPAN_DAYS = 14  # Need at least this many days between first and last weigh-in to measure.
MIN_WEIGH_INS = 4  # ...and enough weigh-ins that the slope isn't two noisy points.
MIN_LOGGED_DAYS = 10  # ...and enough food-logged days to trust the intake average.
MIN_DENSITY = Decimal("0.5")  # ...covering at least half the span (else logging is too sparse).
FULL_CONFIDENCE_DAYS = 28  # Span at which we fully trust the measured value over the formula.

# Guardrail: a logging gap or a water-weight swing can throw a wild measured value. Keep it
# within a sane band of the formula so a single bad window can't wreck the target.
CLAMP_LOW = Decimal("0.65")
CLAMP_HIGH = Decimal("1.5")

Point = tuple[date, Decimal | int | float | str]


@dataclass(frozen=True)
class AdaptiveResult:
    """What the API reports and uses. ``maintenance`` is the value to actually feed the target."""

    maintenance: Decimal  # blended (or pure formula when measured is None)
    formula: Decimal  # the Mifflin × activity estimate, echoed for transparency
    measured: Decimal | None  # measured TDEE (clamped), or None when data is insufficient
    confidence: Decimal  # 0..1 weight given to the measured value
    logged_days: int
    span_days: int


def _dec(value: Decimal | int | float | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal(value)


def measured_tdee(
    mean_daily_intake: Decimal | int | float | str,
    weight_delta_kg: Decimal | int | float | str,
    days: int,
) -> Decimal:
    """Maintenance implied by energy balance: intake minus the energy that became weight."""
    return _dec(mean_daily_intake) - (_dec(weight_delta_kg) * KCAL_PER_KG) / _dec(days)


def weight_slope_kg_per_day(points: list[Point]) -> Decimal | None:
    """Least-squares slope of weight vs. day index (kg/day). None if degenerate (all same day)."""
    if len(points) < 2:
        return None
    base = min(d for d, _ in points)
    xs = [Decimal((d - base).days) for d, _ in points]
    ys = [_dec(w) for _, w in points]
    n = Decimal(len(points))
    sx, sy = sum(xs, Decimal(0)), sum(ys, Decimal(0))
    sxx = sum((x * x for x in xs), Decimal(0))
    sxy = sum((x * y for x, y in zip(xs, ys)), Decimal(0))
    denom = n * sxx - sx * sx
    if denom == 0:  # every weigh-in on the same day → no slope
        return None
    return (n * sxy - sx * sy) / denom


def _confidence(span_days: int) -> Decimal:
    """Ramp 0→1 as the span grows from MIN_SPAN_DAYS to FULL_CONFIDENCE_DAYS."""
    span = Decimal(span_days)
    lo, hi = Decimal(MIN_SPAN_DAYS), Decimal(FULL_CONFIDENCE_DAYS)
    if span <= lo:
        return Decimal(0)
    return min(Decimal(1), (span - lo) / (hi - lo))


def adaptive_maintenance(
    *,
    formula: Decimal | int | float | str,
    weigh_points: list[Point],
    intake_by_day: dict[date, Decimal],
    today: date,
    activity_by_day: dict[date, Decimal] | None = None,
    activity_floor: Decimal | int | float | str = 0,
    window_days: int = WINDOW_DAYS,
) -> AdaptiveResult:
    """Blend the formula maintenance with a measured *baseline* maintenance when enough recent
    data exists.

    ``intake_by_day`` maps a date → that day's total kcal (logged days only). The current day
    is excluded from the intake average since its log is still partial.

    ``activity_by_day`` maps a date → that day's activity kcal (steps + workouts). Energy balance
    measures *total* expenditure; ``measured`` should instead be comparable to the ``formula``,
    which already includes an occupational activity allowance (``activity_floor`` = formula − BMR,
    e.g. BMR × 0.2 for a desk job). So we subtract only the window's mean activity **above**
    ``activity_floor`` — the deliberate exercise / extra movement the formula doesn't cover —
    leaving everyday activity in the baseline. Omit both (or pass empty / 0) to get the raw
    total-expenditure measurement.
    """
    formula = _dec(formula)
    nil = AdaptiveResult(formula, formula, None, Decimal(0), 0, 0)

    cutoff = today - timedelta(days=window_days)
    window_weights = sorted(
        ((d, _dec(w)) for d, w in weigh_points if cutoff <= d <= today), key=lambda p: p[0]
    )
    if len(window_weights) < MIN_WEIGH_INS:
        return nil

    start_day, end_day = window_weights[0][0], window_weights[-1][0]
    span_days = (end_day - start_day).days
    if span_days < MIN_SPAN_DAYS:
        return nil

    logged = [
        (d, _dec(kcal))
        for d, kcal in intake_by_day.items()
        if start_day <= d < today and _dec(kcal) > 0
    ]
    logged_days = len(logged)
    density = Decimal(logged_days) / Decimal(span_days + 1)
    if logged_days < MIN_LOGGED_DAYS or density < MIN_DENSITY:
        return AdaptiveResult(formula, formula, None, Decimal(0), logged_days, span_days)

    slope = weight_slope_kg_per_day(window_weights)
    if slope is None:
        return AdaptiveResult(formula, formula, None, Decimal(0), logged_days, span_days)

    mean_intake = sum((k for _, k in logged), Decimal(0)) / Decimal(logged_days)
    delta = slope * Decimal(span_days)
    raw_total = measured_tdee(mean_intake, delta, span_days)  # incl. exercise (energy balance)

    # Subtract only the mean activity ABOVE the formula's occupational allowance (over the SAME
    # logged days), so `measured` keeps everyday activity in the baseline and stays comparable to
    # the formula — only deliberate exercise / extra movement is excluded. Empty activity or
    # activity ≤ floor → excess 0 → raw total (backward compatible).
    activity = activity_by_day or {}
    mean_activity = sum(
        (_dec(activity.get(d, 0)) for d, _ in logged), Decimal(0)
    ) / Decimal(logged_days)
    excess_activity = max(Decimal(0), mean_activity - _dec(activity_floor))
    raw_base = raw_total - excess_activity
    measured = min(max(raw_base, formula * CLAMP_LOW), formula * CLAMP_HIGH)

    confidence = _confidence(span_days)
    blended = formula * (Decimal(1) - confidence) + measured * confidence
    return AdaptiveResult(blended, formula, measured, confidence, logged_days, span_days)
