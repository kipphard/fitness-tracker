"""Weight-trend unit tests — weekly averages, EWMA, and effective-weight selection.

Reference dates: 2026-06-01 is a Monday, so 06-01..06-07 is one ISO week and 06-08 starts
the next.
"""
from datetime import date
from decimal import Decimal

from backend.weight import trend
from backend.weight.trend import WeightSource

POINTS = [
    (date(2026, 6, 1), Decimal("100")),
    (date(2026, 6, 3), Decimal("102")),
    (date(2026, 6, 8), Decimal("99")),
    (date(2026, 6, 9), Decimal("101")),
]


def test_weekly_averages_groups_by_iso_week():
    weeks = trend.weekly_averages(POINTS)
    assert [(w.week_start, w.average, w.count) for w in weeks] == [
        (date(2026, 6, 1), Decimal("101"), 2),
        (date(2026, 6, 8), Decimal("100"), 2),
    ]


def test_ewma_trend_known_values():
    points = [
        (date(2026, 6, 1), Decimal("100")),
        (date(2026, 6, 2), Decimal("102")),
        (date(2026, 6, 3), Decimal("98")),
    ]
    series = trend.ewma_trend(points, alpha=Decimal("0.1"))
    assert [p.trend for p in series] == [
        Decimal("100"),
        Decimal("100.2"),  # 0.1*102 + 0.9*100
        Decimal("99.98"),  # 0.1*98  + 0.9*100.2
    ]


def test_last_completed_week_average():
    assert trend.last_completed_week_average(POINTS, date(2026, 6, 15)) == Decimal("100")
    assert trend.last_completed_week_average(POINTS, date(2026, 6, 10)) == Decimal("101")
    assert trend.last_completed_week_average(POINTS, date(2026, 6, 3)) is None


def test_effective_weight_prefers_completed_week():
    points = [(date(2026, 6, 1), Decimal("100")), (date(2026, 6, 8), Decimal("99"))]
    # 06-10 is in week B (current); only week A is completed -> its average.
    w, src = trend.effective_weight(points, date(2026, 6, 10), Decimal("80"))
    assert (w, src) == (Decimal("100"), WeightSource.weekly_average)


def test_effective_weight_falls_back_to_latest_then_profile():
    # Only current-week data -> latest weigh-in.
    current = [(date(2026, 6, 8), Decimal("99")), (date(2026, 6, 9), Decimal("98"))]
    assert trend.effective_weight(current, date(2026, 6, 10), Decimal("80")) == (
        Decimal("98"),
        WeightSource.latest_weigh_in,
    )
    # No data at all -> profile fallback.
    assert trend.effective_weight([], date(2026, 6, 10), Decimal("80")) == (
        Decimal("80"),
        WeightSource.profile,
    )


def test_weekly_change():
    points = [(date(2026, 6, 1), Decimal("100")), (date(2026, 6, 8), Decimal("99"))]
    # 06-15 (week C): weeks A (100) and B (99) completed -> change = 99 - 100
    assert trend.weekly_change(points, date(2026, 6, 15)) == Decimal("-1")
    # 06-10 (week B): only A completed -> not enough data
    assert trend.weekly_change(points, date(2026, 6, 10)) is None
