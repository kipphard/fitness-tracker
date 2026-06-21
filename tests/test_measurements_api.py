"""Body measurement API tests."""
from datetime import date
from decimal import Decimal


def test_upsert_and_partial_update(client):
    r = client.put(
        "/api/measurements",
        json={"date": "2026-06-01", "waist_cm": "85", "chest_cm": "105"},
    ).json()
    assert Decimal(r["waist_cm"]) == Decimal("85")
    assert Decimal(r["chest_cm"]) == Decimal("105")
    assert r["arm_cm"] is None

    # Partial update keeps the previously-set fields.
    r2 = client.put(
        "/api/measurements", json={"date": "2026-06-01", "arm_cm": "38"}
    ).json()
    assert Decimal(r2["arm_cm"]) == Decimal("38")
    assert Decimal(r2["waist_cm"]) == Decimal("85")

    assert len(client.get("/api/measurements").json()) == 1


def test_measurement_defaults_to_today(client):
    r = client.put("/api/measurements", json={"waist_cm": "80"}).json()
    assert r["date"] == date.today().isoformat()


def test_measurements_isolated_per_user(client, second_client):
    client.put("/api/measurements", json={"date": "2026-06-01", "waist_cm": "85"})
    assert second_client.get("/api/measurements").json() == []
