"""User-defined meal-slot endpoints + diary slot validation."""


def _custom_key(slots):
    return next(s["key"] for s in slots if not s["builtin"])


def test_defaults_for_fresh_user(client):
    resp = client.get("/api/meal-slots")
    assert resp.status_code == 200, resp.text
    slots = resp.json()
    assert [s["key"] for s in slots] == ["breakfast", "lunch", "dinner", "snack"]
    assert all(s["builtin"] and s["label"] is None for s in slots)


def test_add_custom_slot_and_log_to_it(client):
    put = client.put(
        "/api/meal-slots",
        json={
            "slots": [
                {"key": "breakfast"},
                {"label": "Pre-Workout"},
                {"key": "lunch"},
                {"key": "dinner"},
                {"key": "snack"},
            ]
        },
    )
    assert put.status_code == 200, put.text
    slots = put.json()
    key = _custom_key(slots)
    assert key.startswith("custom_")
    # order is preserved: the custom slot sits between breakfast and lunch
    assert [s["key"] for s in slots][:3] == ["breakfast", key, "lunch"]

    # GET reflects the new slot
    assert any(s["key"] == key for s in client.get("/api/meal-slots").json())

    # log a food to the custom slot
    logged = client.post(
        "/api/diary",
        json={"slot": key, "amount_g": "100", "food": {"name": "Shake", "per100_kcal": "120"}},
    )
    assert logged.status_code == 201, logged.text
    assert logged.json()["slot"] == key

    # it shows up in the day
    day = client.get("/api/diary").json()
    assert any(e["slot"] == key for e in day["entries"])


def test_log_to_unknown_slot_rejected(client):
    resp = client.post(
        "/api/diary",
        json={"slot": "not-a-slot", "amount_g": "100", "food": {"name": "X", "per100_kcal": "10"}},
    )
    assert resp.status_code == 422


def test_rename_custom_slot_keeps_key(client):
    key = _custom_key(
        client.put("/api/meal-slots", json={"slots": [{"label": "Elevenses"}]}).json()
    )
    renamed = client.put(
        "/api/meal-slots", json={"slots": [{"key": key, "label": "Second Breakfast"}]}
    ).json()
    match = next(s for s in renamed if s["key"] == key)
    assert match["label"] == "Second Breakfast"  # same key, new label
