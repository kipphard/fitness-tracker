"""Settings endpoint: food-planning preferences + budget round-trip (issue #5 §2/§4)."""
from decimal import Decimal


def test_settings_food_prefs_round_trip(client):
    # Defaults: the new fields are absent until set.
    initial = client.get("/api/settings").json()
    assert initial["country"] is None
    assert initial["store"] is None
    assert initial["dietary_preferences"] is None

    resp = client.put(
        "/api/settings",
        json={"country": "Germany", "store": "REWE", "dietary_preferences": "vegetarian, no nuts"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["country"] == "Germany"
    assert data["store"] == "REWE"
    assert data["dietary_preferences"] == "vegetarian, no nuts"
    # Persisted, and unrelated settings untouched.
    again = client.get("/api/settings").json()
    assert again["store"] == "REWE"
    assert again["eat_back_activity"] is False


def test_settings_budget_round_trip(client):
    resp = client.put("/api/settings", json={"food_budget_weekly": "60.00", "currency": "EUR"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["currency"] == "EUR"
    assert Decimal(data["food_budget_weekly"]) == Decimal("60.00")
    # An explicit null clears the budget (exclude_unset) but leaves currency untouched.
    cleared = client.put("/api/settings", json={"food_budget_weekly": None}).json()
    assert cleared["food_budget_weekly"] is None
    assert cleared["currency"] == "EUR"


def test_settings_shoe_size_round_trip(client):
    """Shoe size (#13) persists and is null until set."""
    assert client.get("/api/settings").json()["shoe_size_eu"] is None
    resp = client.put("/api/settings", json={"shoe_size_eu": "42.5"})
    assert resp.status_code == 200, resp.text
    assert Decimal(resp.json()["shoe_size_eu"]) == Decimal("42.5")
    again = client.get("/api/settings").json()
    assert Decimal(again["shoe_size_eu"]) == Decimal("42.5")
