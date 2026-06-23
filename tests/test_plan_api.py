"""Day-plan endpoint tests (Claude is faked in conftest)."""
from decimal import Decimal

PROFILE = {
    "height_cm": "180",
    "age": 30,
    "gender": "male",
    "weight_kg": "80",
    "activity_level": "sedentary",
    "goal": "maintain",  # target ~2136 kcal
}


def _setup(client):
    client.put("/api/profile", json=PROFILE)
    foods = [
        ("Chicken breast", "165", "31", "4", "0"),
        ("Rice", "130", "2", "0", "28"),
        ("Salmon", "208", "20", "13", "0"),
        ("Oats", "380", "13", "7", "60"),
        ("Yogurt", "59", "10", "0", "4"),
        ("Almonds", "579", "21", "50", "22"),
    ]
    for name, kcal, p, f, c in foods:
        client.post(
            "/api/food",
            json={
                "name": name,
                "per100_kcal": kcal,
                "per100_protein_g": p,
                "per100_fat_g": f,
                "per100_carbs_g": c,
            },
        )
    # Log a small breakfast so the food becomes a recent + there's a consumed amount.
    client.post(
        "/api/diary",
        json={"slot": "breakfast", "amount_g": "50",
              "food": {"name": "Toast", "per100_kcal": "260", "per100_carbs_g": "50"}},
    )


def test_plan_rule_builds_a_full_day(client):
    _setup(client)
    resp = client.post("/api/food/plan", json={})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["source"] == "rule"
    assert data["ai_available"] is False  # no key in tests
    assert [m["slot"] for m in data["meals"]] == ["breakfast", "lunch", "dinner", "snack"]
    assert Decimal(data["planned_kcal"]) > 0
    # Each non-empty meal carries its own totals that match its items.
    for meal in data["meals"]:
        items_kcal = sum((Decimal(s["kcal"]) for s in meal["suggestions"]), Decimal(0))
        assert Decimal(meal["kcal"]) == items_kcal


def test_plan_three_meals_has_no_snack(client):
    _setup(client)
    data = client.post("/api/food/plan", json={"meals": 3}).json()
    assert [m["slot"] for m in data["meals"]] == ["breakfast", "lunch", "dinner"]


def test_plan_scope_full_day_targets_more_than_remaining(client):
    _setup(client)
    full = client.post("/api/food/plan", json={"scope": "full_day"}).json()
    remaining = client.post("/api/food/plan", json={"scope": "remaining"}).json()
    # full-day target includes the already-consumed breakfast; remaining does not.
    assert Decimal(full["target_kcal"]) > Decimal(remaining["target_kcal"])


def test_plan_ai_returns_faked_plan_and_matches_saved_food(client):
    _setup(client)
    resp = client.post("/api/food/plan/ai", json={})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["source"] == "ai"
    assert data["ai_available"] is True
    assert data["notes"]
    items = {s["name"]: s for m in data["meals"] for s in m["suggestions"]}
    assert "Greek yogurt" in items and items["Greek yogurt"]["food_id"] is None
    # "Chicken breast" exists as a saved food → the AI item reuses its food_id.
    assert "Chicken breast" in items and items["Chicken breast"]["food_id"] is not None


def test_plan_ai_503_without_key(client):
    from backend.api.deps import get_suggest_client
    from backend.main import app

    _setup(client)
    app.dependency_overrides.pop(get_suggest_client, None)  # use the real 503 gate
    resp = client.post("/api/food/plan/ai", json={})
    assert resp.status_code == 503


def test_plan_requires_profile(client):
    resp = client.post("/api/food/plan", json={})
    assert resp.status_code == 404


def test_plan_requires_auth(client):
    resp = client.post(
        "/api/food/plan",
        headers={"Authorization": "Bearer not-a-real-token"},
        json={},
    )
    assert resp.status_code == 401
