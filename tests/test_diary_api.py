"""Food catalogue + diary API tests (Open Food Facts is faked in conftest)."""
from datetime import date
from decimal import Decimal

PROFILE = {
    "height_cm": "180",
    "age": 30,
    "gender": "male",
    "weight_kg": "80",
    "activity_level": "sedentary",
    "goal": "maintain",
}
BARCODE = "4011200296908"


def test_barcode_lookup_caches_food(client):
    f = client.get(f"/api/food/barcode/{BARCODE}").json()
    assert f["name"] == "Test Bar"
    assert f["source"] == "off"
    assert Decimal(f["per100_kcal"]) == Decimal("400")
    # Second lookup returns the cached row (same id, no new fetch).
    f2 = client.get(f"/api/food/barcode/{BARCODE}").json()
    assert f2["id"] == f["id"]


def test_barcode_not_found(client):
    assert client.get("/api/food/barcode/0000000000000").status_code == 404


def test_off_search_is_transient(client):
    res = client.get("/api/food/search", params={"q": "banana"}).json()
    assert len(res) == 1
    assert "banana" in res[0]["name"]
    assert "id" not in res[0]


def test_create_custom_food_and_search_saved(client):
    created = client.post(
        "/api/food",
        json={"name": "My Oats", "per100_kcal": "380", "per100_protein_g": "13"},
    ).json()
    assert created["source"] == "custom"
    found = client.get("/api/food", params={"q": "oats"}).json()
    assert any(f["id"] == created["id"] for f in found)


def test_log_food_by_id_scales_macros(client):
    food = client.get(f"/api/food/barcode/{BARCODE}").json()  # 400 kcal / 100 g
    entry = client.post(
        "/api/diary",
        json={"slot": "breakfast", "amount_g": "50", "food_id": food["id"]},
    ).json()
    assert entry["food_name"] == "Test Bar"
    assert entry["slot"] == "breakfast"
    assert Decimal(entry["kcal"]) == Decimal("200")  # 400 * 0.5


def test_log_inline_food(client):
    entry = client.post(
        "/api/diary",
        json={
            "slot": "lunch",
            "amount_g": "200",
            "food": {"name": "Rice", "per100_kcal": "130", "per100_carbs_g": "28"},
        },
    ).json()
    assert Decimal(entry["kcal"]) == Decimal("260")  # 130 * 2


def test_diary_day_totals(client):
    client.post(
        "/api/diary",
        json={"date": "2026-06-01", "slot": "breakfast", "amount_g": "100",
              "food": {"name": "A", "per100_kcal": "100", "per100_protein_g": "10"}},
    )
    client.post(
        "/api/diary",
        json={"date": "2026-06-01", "slot": "lunch", "amount_g": "200",
              "food": {"name": "B", "per100_kcal": "50", "per100_protein_g": "5"}},
    )
    day = client.get("/api/diary", params={"date": "2026-06-01"}).json()
    assert len(day["entries"]) == 2
    assert Decimal(day["totals"]["kcal"]) == Decimal("200")  # 100 + 100
    assert Decimal(day["totals"]["protein_g"]) == Decimal("20")  # 10 + 10


def test_edit_and_delete_entry(client):
    e = client.post(
        "/api/diary",
        json={"slot": "snack", "amount_g": "100",
              "food": {"name": "C", "per100_kcal": "200", "per100_carbs_g": "50"}},
    ).json()
    patched = client.patch(f"/api/diary/{e['id']}", json={"amount_g": "50"}).json()
    assert Decimal(patched["kcal"]) == Decimal("100")  # recomputed 200 * 0.5
    assert client.delete(f"/api/diary/{e['id']}").status_code == 204
    assert client.get("/api/diary").json()["entries"] == []


def test_copy_day(client):
    client.post(
        "/api/diary",
        json={"date": "2026-06-01", "slot": "breakfast", "amount_g": "100",
              "food": {"name": "A", "per100_kcal": "100"}},
    )
    copied = client.post(
        "/api/diary/copy", json={"from_date": "2026-06-01", "to_date": "2026-06-02"}
    ).json()
    assert copied["date"] == "2026-06-02"
    assert len(copied["entries"]) == 1


def test_copy_selected_entries_only(client):
    a = client.post(
        "/api/diary",
        json={"date": "2026-06-01", "slot": "breakfast", "amount_g": "100",
              "food": {"name": "A", "per100_kcal": "100"}},
    ).json()
    client.post(
        "/api/diary",
        json={"date": "2026-06-01", "slot": "lunch", "amount_g": "100",
              "food": {"name": "B", "per100_kcal": "200"}},
    )
    copied = client.post(
        "/api/diary/copy",
        json={"from_date": "2026-06-01", "to_date": "2026-06-02", "entry_ids": [a["id"]]},
    ).json()
    assert copied["date"] == "2026-06-02"
    assert [e["food_name"] for e in copied["entries"]] == ["A"]
    assert copied["entries"][0]["slot"] == "breakfast"


def test_copy_ignores_unknown_entry_ids(client):
    client.post(
        "/api/diary",
        json={"date": "2026-06-01", "slot": "breakfast", "amount_g": "100",
              "food": {"name": "A", "per100_kcal": "100"}},
    )
    # An id that isn't in from_date (here: a fresh random UUID) is silently skipped.
    copied = client.post(
        "/api/diary/copy",
        json={"from_date": "2026-06-01", "to_date": "2026-06-02",
              "entry_ids": ["00000000-0000-0000-0000-000000000000"]},
    ).json()
    assert copied["entries"] == []


def test_recent_foods(client):
    food = client.get(f"/api/food/barcode/{BARCODE}").json()
    client.post("/api/diary", json={"slot": "breakfast", "amount_g": "50", "food_id": food["id"]})
    recent = client.get("/api/diary/recent").json()
    assert any(f["id"] == food["id"] for f in recent)


def test_today_consumed_and_remaining(client):
    client.put("/api/profile", json=PROFILE)  # maintain -> target 2136
    today_str = date.today().isoformat()
    client.post(
        "/api/diary",
        json={"date": today_str, "slot": "breakfast", "amount_g": "100",
              "food": {"name": "X", "per100_kcal": "500", "per100_protein_g": "20"}},
    )
    t = client.get("/api/today").json()
    assert Decimal(t["consumed"]["kcal"]) == Decimal("500")
    assert Decimal(t["remaining_kcal"]) == Decimal("1636")  # 2136 - 500


def test_food_and_diary_isolated_per_user(client, second_client):
    food = client.get(f"/api/food/barcode/{BARCODE}").json()
    # Second user caches their own food row for the same barcode (different id).
    f2 = second_client.get(f"/api/food/barcode/{BARCODE}").json()
    assert f2["id"] != food["id"]
    assert second_client.get("/api/diary").json()["entries"] == []
