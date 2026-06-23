"""Settings endpoint: food-planning preferences round-trip (issue #5 §2)."""


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
