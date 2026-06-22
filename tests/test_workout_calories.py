"""Pure MET-based workout calorie estimation (issue #3)."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from backend.workouts.calories import DEFAULT_MET, MAX_HOURS, session_kcal

START = datetime(2026, 6, 20, 18, 0, tzinfo=timezone.utc)


def test_finished_session_uses_measured_duration():
    # 5.0 MET × 80 kg × 1 h = 400 kcal
    kcal = session_kcal(
        Decimal("80"), started_at=START, ended_at=START + timedelta(hours=1), set_count=12
    )
    assert kcal == DEFAULT_MET * Decimal("80")


def test_unfinished_session_estimates_from_set_count():
    # No ended_at → 10 sets × 3.5 min = 35 min = 7/12 h; 5 × 80 × 7/12
    kcal = session_kcal(Decimal("80"), started_at=START, ended_at=None, set_count=10)
    assert kcal == DEFAULT_MET * Decimal("80") * (Decimal("35") / Decimal("60"))


def test_duration_is_capped():
    # A session left open for 8 h is clamped to MAX_HOURS so it can't inflate the burn.
    kcal = session_kcal(
        Decimal("80"), started_at=START, ended_at=START + timedelta(hours=8), set_count=5
    )
    assert kcal == DEFAULT_MET * Decimal("80") * MAX_HOURS


def test_override_short_circuits():
    kcal = session_kcal(
        Decimal("80"),
        started_at=START,
        ended_at=START + timedelta(hours=1),
        set_count=12,
        kcal_override=Decimal("250"),
    )
    assert kcal == Decimal("250")


def test_custom_met():
    kcal = session_kcal(
        Decimal("100"),
        started_at=START,
        ended_at=START + timedelta(hours=1),
        set_count=8,
        met=Decimal("6"),
    )
    assert kcal == Decimal("600")


def test_empty_unfinished_session_is_zero():
    assert session_kcal(Decimal("80"), started_at=START, ended_at=None, set_count=0) == Decimal("0")
