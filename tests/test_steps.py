"""Step conversion + steps API + Today net-deficit / eat-back tests."""
from datetime import date
from decimal import Decimal

from backend.steps.convert import steps_to_kcal

PROFILE = {
    "height_cm": "180",
    "age": 30,
    "gender": "male",
    "weight_kg": "80",
    "activity_level": "sedentary",
    "goal": "maintain",
}


def test_steps_to_kcal():
    assert steps_to_kcal(10000, Decimal("95")) == Decimal("475")  # 10000 * 0.0005 * 95
    assert steps_to_kcal(0, Decimal("80")) == Decimal("0")


def test_log_and_get_steps(client):
    client.put("/api/profile", json=PROFILE)
    r = client.put("/api/steps", json={"steps": 10000}).json()
    assert r["steps"] == 10000
    assert Decimal(r["kcal"]) == Decimal("400")  # 10000 * 0.0005 * 80
    assert client.get("/api/steps").json()["steps"] == 10000


def test_steps_default_zero(client):
    client.put("/api/profile", json=PROFILE)
    got = client.get("/api/steps").json()
    assert got["steps"] == 0
    assert Decimal(got["kcal"]) == Decimal("0")


def test_steps_upsert(client):
    client.put("/api/steps", json={"date": "2026-06-01", "steps": 5000})
    client.put("/api/steps", json={"date": "2026-06-01", "steps": 8000})
    got = client.get("/api/steps", params={"date": "2026-06-01"}).json()
    assert got["steps"] == 8000


def test_today_net_deficit_and_eat_back(client):
    client.put("/api/profile", json=PROFILE)  # maintain -> target & maintenance = 2136
    today_str = date.today().isoformat()
    client.put("/api/steps", json={"date": today_str, "steps": 10000})  # 400 kcal
    client.post(
        "/api/diary",
        json={"date": today_str, "slot": "breakfast", "amount_g": "100",
              "food": {"name": "X", "per100_kcal": "500"}},
    )

    t = client.get("/api/today").json()
    assert t["steps"] == 10000
    assert Decimal(t["activity_kcal"]) == Decimal("400")
    # net deficit = (maintenance 2136 + activity 400) - consumed 500
    assert Decimal(t["net_deficit_kcal"]) == Decimal("2036")
    # eat-back off by default -> remaining = target 2136 - consumed 500
    assert t["eat_back_activity"] is False
    assert Decimal(t["remaining_kcal"]) == Decimal("1636")

    client.put("/api/settings", json={"eat_back_activity": True})
    t2 = client.get("/api/today").json()
    assert t2["eat_back_activity"] is True
    # remaining now adds the activity back: 2136 + 400 - 500
    assert Decimal(t2["remaining_kcal"]) == Decimal("2036")


def test_steps_isolated_per_user(client, second_client):
    client.put("/api/steps", json={"steps": 12000})
    assert second_client.get("/api/steps").json()["steps"] == 0
