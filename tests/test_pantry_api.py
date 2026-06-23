"""Pantry endpoint tests (issue #5 §2)."""
import uuid


def _make_food(client, name="Chicken breast"):
    return client.post(
        "/api/food",
        json={"name": name, "per100_kcal": "165", "per100_protein_g": "31"},
    ).json()


def test_add_list_remove_pantry(client):
    food = _make_food(client)
    add = client.post("/api/pantry", json={"food_id": food["id"]})
    assert add.status_code == 201, add.text
    assert add.json()["food"]["name"] == "Chicken breast"

    items = client.get("/api/pantry").json()
    assert [i["food"]["id"] for i in items] == [food["id"]]

    # Idempotent: adding again doesn't duplicate.
    client.post("/api/pantry", json={"food_id": food["id"]})
    assert len(client.get("/api/pantry").json()) == 1

    rm = client.delete(f"/api/pantry/{food['id']}")
    assert rm.status_code == 204
    assert client.get("/api/pantry").json() == []


def test_add_unknown_food_404(client):
    resp = client.post("/api/pantry", json={"food_id": str(uuid.uuid4())})
    assert resp.status_code == 404


def test_remove_not_in_pantry_404(client):
    food = _make_food(client)
    resp = client.delete(f"/api/pantry/{food['id']}")
    assert resp.status_code == 404


def test_pantry_requires_auth(client):
    resp = client.get("/api/pantry", headers={"Authorization": "Bearer nope"})
    assert resp.status_code == 401


def test_pantry_isolated_per_user(client, second_client):
    food = _make_food(client)
    client.post("/api/pantry", json={"food_id": food["id"]})
    # The other user can't see or delete user-a's pantry food.
    assert second_client.get("/api/pantry").json() == []
    assert second_client.delete(f"/api/pantry/{food['id']}").status_code == 404


def test_pantry_food_preferred_in_suggestions(client):
    """A food in the pantry should surface in the rule suggestions over the same-size budget."""
    client.put(
        "/api/profile",
        json={"height_cm": "180", "age": 30, "gender": "male",
              "weight_kg": "80", "activity_level": "sedentary", "goal": "maintain"},
    )
    # Two distinct protein foods; mark one as "at home".
    a = client.post("/api/food", json={"name": "Tofu", "per100_kcal": "144",
                                       "per100_protein_g": "17", "per100_carbs_g": "3"}).json()
    client.post("/api/food", json={"name": "Tempeh", "per100_kcal": "192",
                                   "per100_protein_g": "20", "per100_carbs_g": "8"})
    client.post("/api/pantry", json={"food_id": a["id"]})
    names = [s["name"] for s in client.post("/api/food/suggest", json={}).json()["suggestions"]]
    assert "Tofu" in names  # the pantry food made the basket
