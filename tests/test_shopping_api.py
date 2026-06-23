"""Shopping-list endpoint tests (issue #5 §3)."""
from decimal import Decimal


def _food(client, name, **extra):
    body = {"name": name, "per100_kcal": "150", **extra}
    return client.post("/api/food", json=body).json()


def test_manual_add_merges_by_name(client):
    a = client.post("/api/shopping", json={"name": "Milk", "amount_g": "1000"})
    assert a.status_code == 201, a.text
    # Same name (case-insensitive) updates the one row rather than duplicating.
    client.post("/api/shopping", json={"name": "milk", "amount_g": "500"})
    items = client.get("/api/shopping").json()
    assert len(items) == 1
    assert items[0]["name"] == "milk"
    assert Decimal(items[0]["amount_g"]) == Decimal("500")


def test_from_plan_excludes_pantry_and_aggregates(client):
    rice = _food(client, "Rice")
    chicken = _food(client, "Chicken")
    client.post("/api/pantry", json={"food_id": chicken["id"]})  # already at home

    payload = {
        "items": [
            {"name": "Rice", "food_id": rice["id"], "amount_g": "100"},
            {"name": "Rice", "food_id": rice["id"], "amount_g": "50"},
            {"name": "Chicken", "food_id": chicken["id"], "amount_g": "200"},
            {"name": "Olive oil"},  # novel item, no food_id / amount
        ]
    }
    out = client.post("/api/shopping/from-plan", json=payload).json()
    by_name = {i["name"]: i for i in out}
    assert "Chicken" not in by_name  # in the pantry → dropped
    assert Decimal(by_name["Rice"]["amount_g"]) == Decimal("150")  # 100 + 50 aggregated
    assert by_name["Olive oil"]["amount_g"] is None


def test_check_and_clear(client):
    client.post("/api/shopping", json={"name": "Eggs"})
    client.post("/api/shopping", json={"name": "Bread"})
    items = client.get("/api/shopping").json()
    eggs = next(i for i in items if i["name"] == "Eggs")

    patched = client.patch(f"/api/shopping/{eggs['id']}", json={"checked": True})
    assert patched.status_code == 200 and patched.json()["checked"] is True

    # Clear only checked → Bread remains.
    client.delete("/api/shopping?checked=true")
    remaining = client.get("/api/shopping").json()
    assert [i["name"] for i in remaining] == ["Bread"]

    # Clear all.
    client.delete("/api/shopping")
    assert client.get("/api/shopping").json() == []


def test_remove_and_404(client):
    import uuid

    created = client.post("/api/shopping", json={"name": "Butter"}).json()
    assert client.delete(f"/api/shopping/{created['id']}").status_code == 204
    assert client.delete(f"/api/shopping/{created['id']}").status_code == 404
    assert client.patch(f"/api/shopping/{uuid.uuid4()}", json={"checked": True}).status_code == 404


def test_shopping_price_and_partial_patch(client):
    created = client.post("/api/shopping", json={"name": "Rice", "price": "1.50"}).json()
    assert Decimal(created["price"]) == Decimal("1.50")

    # Ticking it off must not wipe the price (PATCH applies only the sent fields).
    client.patch(f"/api/shopping/{created['id']}", json={"checked": True})
    item = client.get("/api/shopping").json()[0]
    assert item["checked"] is True and Decimal(item["price"]) == Decimal("1.50")

    # Update only the price.
    client.patch(f"/api/shopping/{created['id']}", json={"price": "2.00"})
    assert Decimal(client.get("/api/shopping").json()[0]["price"]) == Decimal("2.00")

    # An explicit null clears the price.
    client.patch(f"/api/shopping/{created['id']}", json={"price": None})
    assert client.get("/api/shopping").json()[0]["price"] is None


def test_shopping_isolated_per_user(client, second_client):
    client.post("/api/shopping", json={"name": "Secret snack"})
    assert second_client.get("/api/shopping").json() == []


def test_shopping_requires_auth(client):
    assert client.get("/api/shopping", headers={"Authorization": "Bearer nope"}).status_code == 401
