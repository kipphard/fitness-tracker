"""Weight API tests — weigh-in CRUD, trend, and the calorie feedback on /calories/me."""
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


def test_log_and_list_weigh_ins(client):
    client.put("/api/weight", json={"date": "2026-06-01", "weight_kg": "100.0"})
    client.put("/api/weight", json={"date": "2026-06-02", "weight_kg": "99.5"})
    rows = client.get("/api/weight").json()
    assert [r["date"] for r in rows] == ["2026-06-01", "2026-06-02"]
    assert Decimal(rows[0]["weight_kg"]) == Decimal("100.0")


def test_upsert_same_day_overwrites(client):
    client.put("/api/weight", json={"date": "2026-06-01", "weight_kg": "100"})
    client.put("/api/weight", json={"date": "2026-06-01", "weight_kg": "98"})
    rows = client.get("/api/weight").json()
    assert len(rows) == 1
    assert Decimal(rows[0]["weight_kg"]) == Decimal("98")


def test_default_date_is_today(client):
    body = client.put("/api/weight", json={"weight_kg": "77"}).json()
    assert body["date"] == date.today().isoformat()


def test_delete_weigh_in(client):
    client.put("/api/weight", json={"date": "2026-06-01", "weight_kg": "100"})
    assert client.delete("/api/weight/2026-06-01").status_code == 204
    assert client.get("/api/weight").json() == []


def test_trend_endpoint(client):
    client.put("/api/weight", json={"date": "2026-06-01", "weight_kg": "100"})
    client.put("/api/weight", json={"date": "2026-06-02", "weight_kg": "102"})
    t = client.get("/api/weight/trend").json()
    assert len(t["points"]) == 2
    assert len(t["ewma"]) == 2
    assert t["weekly"][0]["week_start"] == "2026-06-01"
    assert Decimal(t["weekly"][0]["average"]) == Decimal("101")
    assert t["current_trend"] is not None


def test_calories_me_uses_weekly_average_weight(client):
    client.put("/api/profile", json=PROFILE)
    today = date.today()
    last_week = (today - timedelta(days=10)).isoformat()
    client.put("/api/weight", json={"date": last_week, "weight_kg": "90"})
    client.put("/api/weight", json={"date": today.isoformat(), "weight_kg": "88"})

    me = client.get("/api/calories/me").json()
    assert me["weight_source"] == "weekly_average"
    assert Decimal(me["weight_kg"]) == Decimal("90")
    # BMR uses 90 (last completed week), not the profile's 80:
    # 10*90 + 6.25*180 - 5*30 + 5 = 1880
    assert Decimal(me["bmr"]) == Decimal("1880")


def test_calories_me_falls_back_to_profile_weight(client):
    client.put("/api/profile", json=PROFILE)
    me = client.get("/api/calories/me").json()
    assert me["weight_source"] == "profile"
    assert Decimal(me["weight_kg"]) == Decimal("80")
    assert Decimal(me["bmr"]) == Decimal("1780")


def test_weight_isolated_per_user(client, second_client):
    client.put("/api/weight", json={"date": "2026-06-01", "weight_kg": "100"})
    assert second_client.get("/api/weight").json() == []
