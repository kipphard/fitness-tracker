"""Fill-remaining-calories endpoint tests (Claude is faked in conftest)."""
from datetime import date
from decimal import Decimal

PROFILE = {
    "height_cm": "180",
    "age": 30,
    "gender": "male",
    "weight_kg": "80",
    "activity_level": "sedentary",
    "goal": "maintain",  # target ~2136 kcal
}


def _setup(client, *, breakfast_g="100"):
    client.put("/api/profile", json=PROFILE)
    today = date.today().isoformat()
    # Log a small breakfast so there's a real remaining budget + a candidate food (recent).
    client.post(
        "/api/diary",
        json={
            "date": today,
            "slot": "breakfast",
            "amount_g": breakfast_g,
            "food": {
                "name": "Oats",
                "per100_kcal": "380",
                "per100_protein_g": "13",
                "per100_fat_g": "7",
                "per100_carbs_g": "60",
            },
        },
    )
    # A protein-dense saved food the engine can surface for the protein gap.
    client.post(
        "/api/food",
        json={
            "name": "Chicken breast",
            "per100_kcal": "165",
            "per100_protein_g": "31",
            "per100_fat_g": "4",
            "per100_carbs_g": "0",
        },
    )


def test_suggest_returns_foods_to_fill_gap(client):
    _setup(client)
    resp = client.post("/api/food/suggest", json={})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["source"] == "rule"
    assert Decimal(data["remaining_kcal"]) > 0
    assert len(data["suggestions"]) > 0
    s = data["suggestions"][0]
    assert Decimal(s["amount_g"]) > 0
    assert Decimal(s["kcal"]) > 0
    assert s["food_id"] is not None  # rule-based suggestions reference saved foods


def test_suggest_ai_not_configured_in_tests(client):
    """No ANTHROPIC_API_KEY in the test env → the rule endpoint reports AI unavailable."""
    _setup(client)
    data = client.post("/api/food/suggest", json={}).json()
    assert data["ai_available"] is False


def test_suggest_empty_when_over_budget(client):
    client.put("/api/profile", json=PROFILE)
    today = date.today().isoformat()
    client.post(
        "/api/diary",
        json={
            "date": today,
            "slot": "lunch",
            "amount_g": "1000",  # 1000 g * 500 kcal/100g = 5000 kcal, well over target
            "food": {"name": "Feast", "per100_kcal": "500"},
        },
    )
    data = client.post("/api/food/suggest", json={}).json()
    assert Decimal(data["remaining_kcal"]) < 0
    assert data["suggestions"] == []


def test_suggest_ai_returns_faked_suggestion(client):
    _setup(client)
    resp = client.post("/api/food/suggest/ai", json={"preferences": "high protein"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["source"] == "ai"
    assert data["ai_available"] is True
    names = [s["name"] for s in data["suggestions"]]
    assert "Greek yogurt" in names
    assert data["notes"]


def test_suggest_requires_profile(client):
    resp = client.post("/api/food/suggest", json={})
    assert resp.status_code == 404  # no profile yet


def test_suggest_requires_auth(client):
    resp = client.post(
        "/api/food/suggest",
        headers={"Authorization": "Bearer not-a-real-token"},
        json={},
    )
    assert resp.status_code == 401
