"""Macro prefs + Today dashboard API tests."""
from decimal import Decimal

PROFILE = {
    "height_cm": "180",
    "age": 30,
    "gender": "male",
    "weight_kg": "80",
    "activity_level": "sedentary",
    "goal": "maintain",
}


def test_macro_prefs_defaults_and_update(client):
    got = client.get("/api/macros").json()
    assert Decimal(got["protein_g_per_kg"]) == Decimal("2.0")
    assert Decimal(got["fat_g_per_kg"]) == Decimal("0.8")

    upd = client.put("/api/macros", json={"protein_g_per_kg": "2.2"}).json()
    assert Decimal(upd["protein_g_per_kg"]) == Decimal("2.2")
    assert Decimal(upd["fat_g_per_kg"]) == Decimal("0.8")  # unchanged


def test_today_requires_profile(client):
    assert client.get("/api/today").status_code == 404


def test_today_returns_calories_and_reconciled_macros(client):
    client.put("/api/profile", json=PROFILE)
    today = client.get("/api/today").json()
    cals, macros = today["calories"], today["macros"]

    # maintain -> target == maintenance == 1780 * 1.2
    assert Decimal(cals["target"]) == Decimal("2136.0")
    assert cals["weight_source"] == "profile"  # no weigh-ins yet
    # default macros on 80 kg: 160 g protein, 64 g fat; carbs fill 2136-640-576 = 920 kcal
    assert Decimal(macros["protein_g"]) == Decimal("160")
    assert Decimal(macros["fat_g"]) == Decimal("64")
    assert Decimal(macros["carbs_kcal"]) == Decimal("920")
    assert macros["reconciled"] is True


def test_today_macros_follow_pref_change(client):
    client.put("/api/profile", json=PROFILE)
    client.put("/api/macros", json={"protein_g_per_kg": "2.5"})
    macros = client.get("/api/today").json()["macros"]
    assert Decimal(macros["protein_g"]) == Decimal("200")  # 80 * 2.5


def test_macros_isolated_per_user(client, second_client):
    client.put("/api/macros", json={"protein_g_per_kg": "2.5"})
    other = second_client.get("/api/macros").json()
    assert Decimal(other["protein_g_per_kg"]) == Decimal("2.0")  # default, not 2.5
