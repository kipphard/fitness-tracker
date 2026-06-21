"""Pure weight-trend package (Phase 2)."""
from backend.weight.trend import (
    EWMA_ALPHA,
    TrendPoint,
    WeekAverage,
    WeightSource,
    effective_weight,
    ewma_trend,
    last_completed_week_average,
    latest_weight,
    weekly_averages,
)

__all__ = [
    "EWMA_ALPHA",
    "TrendPoint",
    "WeekAverage",
    "WeightSource",
    "effective_weight",
    "ewma_trend",
    "last_completed_week_average",
    "latest_weight",
    "weekly_averages",
]
