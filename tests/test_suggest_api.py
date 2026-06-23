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


# --- editable serving sizes ------------------------------------------------

def test_edit_food_serving(client):
    created = client.post(
        "/api/food", json={"name": "Quark", "per100_kcal": "68", "per100_protein_g": "12"}
    ).json()
    patched = client.patch(f"/api/food/{created['id']}", json={"serving_g": "250"})
    assert patched.status_code == 200, patched.text
    assert Decimal(patched.json()["serving_g"]) == Decimal("250")


def test_edit_food_not_found(client):
    import uuid

    resp = client.patch(f"/api/food/{uuid.uuid4()}", json={"serving_g": "100"})
    assert resp.status_code == 404


# --- backfill servings from OFF --------------------------------------------

def test_backfill_servings_fills_missing(client, session_factory):
    from decimal import Decimal as D

    from backend.persistence import repository
    from backend.persistence.models import FoodSource

    s = session_factory()
    user = repository.get_user_by_email(s, "user-a@example.com")
    repository.create_food(
        s,
        user.id,
        source=FoodSource.off,
        name="No-serving bar",
        barcode="9999",  # _FakeOFF returns serving_g=40 for this
        per100_kcal=D("400"),
        per100_protein_g=D("20"),
        per100_fat_g=D("10"),
        per100_carbs_g=D("50"),
        serving_g=None,
    )
    s.commit()
    s.close()

    resp = client.post("/api/food/backfill-servings")
    assert resp.status_code == 200, resp.text
    assert resp.json()["updated"] >= 1


# --- regenerate / swap -----------------------------------------------------

def _setup_many(client):
    client.put("/api/profile", json=PROFILE)
    foods = [
        ("Chicken", "165", "31", "4", "0"),
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
    # log one so there's a recent + a real remaining budget
    client.post(
        "/api/diary",
        json={"slot": "breakfast", "amount_g": "50",
              "food": {"name": "Toast", "per100_kcal": "260", "per100_carbs_g": "50"}},
    )


def test_suggest_regenerate_excludes_shown_foods(client):
    _setup_many(client)
    first = client.post("/api/food/suggest", json={}).json()["suggestions"]
    ids = [s["food_id"] for s in first if s["food_id"]]
    assert ids
    again = client.post("/api/food/suggest", json={"exclude_food_ids": ids}).json()["suggestions"]
    again_ids = {s["food_id"] for s in again if s["food_id"]}
    assert again_ids and not (again_ids & set(ids))


def test_suggest_swap_single_item(client):
    _setup_many(client)
    basket = client.post("/api/food/suggest", json={}).json()["suggestions"]
    assert basket
    ids = [s["food_id"] for s in basket if s["food_id"]]
    item = basket[0]
    repl = client.post(
        "/api/food/suggest",
        json={"exclude_food_ids": ids, "count": 1, "target_kcal": item["kcal"]},
    ).json()["suggestions"]
    assert len(repl) <= 1
    if repl:
        assert repl[0]["food_id"] not in ids
