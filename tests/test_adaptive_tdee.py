"""Adaptive TDEE (issue #4): the pure energy-balance module + the /today integration path."""
from datetime import date, timedelta
from decimal import Decimal

from backend.calories import adaptive

TODAY = date(2026, 6, 29)


def _linear_weights(start_kg, slope_per_day, days):
    """Weigh-ins from TODAY-days .. TODAY, declining linearly at slope_per_day kg/day."""
    base = TODAY - timedelta(days=days)
    return [
        (base + timedelta(days=i), Decimal(str(start_kg)) + Decimal(str(slope_per_day)) * i)
        for i in range(days + 1)
    ]


def _intake(days, kcal_per_day):
    """A full kcal log on every day in [TODAY-days, TODAY] (TODAY itself is partial; the
    module drops it, but we include it to prove that)."""
    base = TODAY - timedelta(days=days)
    return {base + timedelta(days=i): Decimal(kcal_per_day) for i in range(days + 1)}


# --- the scalar core -------------------------------------------------------

def test_measured_tdee_energy_balance():
    # Ate 2000/day, lost 1.4 kg over 28 days → maintenance was higher than intake.
    assert adaptive.measured_tdee(2000, Decimal("-1.4"), 28) == Decimal("2385")
    # Gained 1.4 kg on the same intake → maintenance was lower.
    assert adaptive.measured_tdee(2000, Decimal("1.4"), 28) == Decimal("1615")


def test_weight_slope_is_exact_on_a_line():
    pts = [(date(2026, 6, 1), Decimal("82")), (date(2026, 6, 11), Decimal("80"))]
    assert adaptive.weight_slope_kg_per_day(pts) == Decimal("-0.2")


# --- gating: no measured value until there's enough dense data --------------

def test_too_few_weigh_ins_falls_back_to_formula():
    res = adaptive.adaptive_maintenance(
        formula=2136,
        weigh_points=_linear_weights(80, -0.05, 3)[:3],  # 3 points < MIN_WEIGH_INS
        intake_by_day=_intake(28, 2000),
        today=TODAY,
    )
    assert res.measured is None
    assert res.maintenance == Decimal("2136")
    assert res.confidence == Decimal("0")


def test_span_too_short_falls_back_to_formula():
    res = adaptive.adaptive_maintenance(
        formula=2136,
        weigh_points=_linear_weights(80, -0.05, 10),  # 11 points but span 10 < MIN_SPAN_DAYS
        intake_by_day=_intake(28, 2000),
        today=TODAY,
    )
    assert res.measured is None


def test_sparse_logging_falls_back_to_formula():
    sparse = dict(list(_intake(28, 2000).items())[:6])  # only 6 logged days < MIN_LOGGED_DAYS
    res = adaptive.adaptive_maintenance(
        formula=2136, weigh_points=_linear_weights(80, -0.05, 28),
        intake_by_day=sparse, today=TODAY,
    )
    assert res.measured is None
    assert res.maintenance == Decimal("2136")


# --- the measured value, blending, confidence, clamp ------------------------

def test_full_window_trusts_the_measured_value():
    res = adaptive.adaptive_maintenance(
        formula=2136, weigh_points=_linear_weights(80, -0.05, 28),
        intake_by_day=_intake(28, 2000), today=TODAY,
    )
    assert res.span_days == 28
    assert res.logged_days == 28  # TODAY excluded (partial), 28 prior days counted
    assert res.confidence == Decimal("1")  # span == FULL_CONFIDENCE_DAYS
    assert abs(res.measured - Decimal("2385")) < Decimal("0.01")
    assert res.maintenance == res.measured  # confidence 1 → pure measured


def test_confidence_ramps_and_blends():
    res = adaptive.adaptive_maintenance(
        formula=2000, weigh_points=_linear_weights(80, -0.05, 21),
        intake_by_day=_intake(21, 2000), today=TODAY,
    )
    assert res.confidence == Decimal("0.5")  # (21-14)/(28-14)
    # blended = formula*(1-c) + measured*c, strictly between the two
    assert min(res.formula, res.measured) < res.maintenance < max(res.formula, res.measured)


def test_measured_is_clamped_to_a_sane_band():
    # A 0.3 kg/day "loss" implies an absurd TDEE; clamp it to 1.5× formula.
    res = adaptive.adaptive_maintenance(
        formula=2000, weigh_points=_linear_weights(90, -0.3, 28),
        intake_by_day=_intake(28, 1800), today=TODAY,
    )
    assert res.measured == Decimal("3000")  # 2000 * CLAMP_HIGH


# --- integration: the value flows through /today ----------------------------

def test_today_uses_adaptive_maintenance(client):
    client.put("/api/profile", json={
        "height_cm": "180", "age": 30, "gender": "male",
        "weight_kg": "82", "activity_level": "sedentary", "goal": "cut",
    })
    # 27 days of weigh-ins (steady loss) + a full 2000 kcal log each day, ending yesterday.
    today = date.today()
    for i in range(27, 0, -1):
        day = (today - timedelta(days=i)).isoformat()
        client.put("/api/weight", json={"date": day, "weight_kg": str(82 - 0.05 * (27 - i))})
        client.post("/api/diary", json={
            "date": day, "slot": "breakfast", "amount_g": "400",
            "food": {"name": "Day", "per100_kcal": "500"},  # 2000 kcal
        })

    t = client.get("/api/today").json()["calories"]
    measured = Decimal(t["measured_maintenance"])
    formula = Decimal(t["formula_maintenance"])
    maint = Decimal(t["maintenance"])
    assert measured > 0
    assert Decimal(t["tdee_confidence"]) > 0
    # The used maintenance is a convex blend of formula and measured.
    assert min(formula, measured) <= maint <= max(formula, measured)
    # Ate 2000 and lost weight → measured maintenance exceeds intake.
    assert measured > Decimal("2000")


def test_today_without_data_is_pure_formula(client):
    client.put("/api/profile", json={
        "height_cm": "180", "age": 30, "gender": "male",
        "weight_kg": "82", "activity_level": "sedentary", "goal": "maintain",
    })
    t = client.get("/api/today").json()["calories"]
    assert t["measured_maintenance"] is None
    assert Decimal(t["tdee_confidence"]) == Decimal("0")
    assert Decimal(t["maintenance"]) == Decimal(t["formula_maintenance"])
