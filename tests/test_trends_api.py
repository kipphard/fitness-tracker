"""Trends + rate-of-loss guardrail tests."""
from datetime import date, timedelta
from decimal import Decimal

PROFILE = {
    "height_cm": "180",
    "age": 30,
    "gender": "male",
    "weight_kg": "80",
    "activity_level": "sedentary",
    "goal": "maintain",
}


def test_trends_adherence_and_target(client):
    client.put("/api/profile", json=PROFILE)  # maintain -> target 2136
    today = date.today().isoformat()
    client.post(
        "/api/diary",
        json={"date": today, "slot": "breakfast", "amount_g": "100",
              "food": {"name": "X", "per100_kcal": "500"}},
    )
    t = client.get("/api/trends").json()
    assert Decimal(t["target_kcal"]) == Decimal("2136.0")
    assert len(t["adherence"]) == 14
    last = t["adherence"][-1]
    assert last["date"] == today
    assert Decimal(last["consumed"]) == Decimal("500")
    assert Decimal(last["target"]) == Decimal("2136.0")


def test_trends_weekly_change_and_rate_warning(client):
    client.put("/api/profile", json=PROFILE)
    today = date.today()
    client.put("/api/weight", json={"date": (today - timedelta(days=18)).isoformat(), "weight_kg": "100"})
    client.put("/api/weight", json={"date": (today - timedelta(days=11)).isoformat(), "weight_kg": "96"})

    t = client.get("/api/trends").json()
    assert Decimal(t["weekly_change_kg"]) == Decimal("-4")  # 96 - 100 across two completed weeks
    assert t["rate_warning"] is True  # 4 / 96 ≈ 4.2% per week > 1%


def test_trends_no_warning_without_data(client):
    client.put("/api/profile", json=PROFILE)
    t = client.get("/api/trends").json()
    assert t["weekly_change_kg"] is None
    assert t["rate_warning"] is False
