"""Profile, settings, and per-profile calorie endpoint tests."""
from decimal import Decimal

PROFILE = {
    "height_cm": "180",
    "age": 30,
    "gender": "male",
    "weight_kg": "80",
    "activity_level": "sedentary",
    "goal": "cut",
}


def test_profile_404_before_set(client):
    assert client.get("/api/profile").status_code == 404


def test_put_then_get_profile(client):
    put = client.put("/api/profile", json=PROFILE)
    assert put.status_code == 200, put.text
    assert put.json()["gender"] == "male"

    got = client.get("/api/profile")
    assert got.status_code == 200
    body = got.json()
    assert body["activity_level"] == "sedentary"
    assert body["goal"] == "cut"
    assert Decimal(body["weight_kg"]) == Decimal("80")


def test_calories_me_from_saved_profile(client):
    client.put("/api/profile", json=PROFILE)
    resp = client.get("/api/calories/me")
    assert resp.status_code == 200
    data = resp.json()
    # Decimals are delivered as strings.
    assert Decimal(data["bmr"]) == Decimal("1780")
    assert Decimal(data["maintenance"]) == Decimal("2136.0")
    assert Decimal(data["target"]) == Decimal("1636.0")
    assert data["below_floor"] is False


def test_calories_me_404_without_profile(client):
    assert client.get("/api/calories/me").status_code == 404


def test_calculate_is_stateless(client):
    resp = client.post("/api/calories/calculate", json=PROFILE)
    assert resp.status_code == 200
    assert Decimal(resp.json()["target"]) == Decimal("1636.0")


def test_activity_levels_metadata(client):
    resp = client.get("/api/calories/activity-levels")
    assert resp.status_code == 200
    levels = resp.json()
    assert [lvl["key"] for lvl in levels] == [
        "sedentary",
        "lightly_active",
        "moderately_active",
        "heavy",
        "very_heavy",
    ]
    assert Decimal(levels[0]["multiplier"]) == Decimal("1.2")


def test_settings_defaults_and_update(client):
    got = client.get("/api/settings").json()
    assert got["language"] == "en"
    assert got["unit_system"] == "metric"
    assert got["eat_back_activity"] is False

    upd = client.put("/api/settings", json={"language": "de"})
    assert upd.status_code == 200
    assert upd.json()["language"] == "de"
    assert upd.json()["unit_system"] == "metric"


def test_profile_isolated_per_user(client, second_client):
    client.put("/api/profile", json=PROFILE)
    # The second user has their own (absent) profile.
    assert second_client.get("/api/profile").status_code == 404
