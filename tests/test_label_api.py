"""Nutrition-label photo endpoint tests (Claude vision is faked in conftest)."""
from decimal import Decimal


def test_read_label_returns_per100_draft(client):
    resp = client.post(
        "/api/food/photo-label",
        files={"file": ("label.jpg", b"\xff\xd8\xff\xe0fake-jpeg-bytes", "image/jpeg")},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["name"] == "Skyr Vanilla"
    assert Decimal(data["per100_kcal"]) == Decimal("74")
    assert Decimal(data["per100_protein_g"]) == Decimal("10")
    assert Decimal(data["per100_carbs_g"]) == Decimal("7.5")
    assert Decimal(data["serving_g"]) == Decimal("150")


def test_read_label_rejects_non_image(client):
    resp = client.post(
        "/api/food/photo-label",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 415


def test_read_label_rejects_empty_file(client):
    resp = client.post(
        "/api/food/photo-label",
        files={"file": ("label.jpg", b"", "image/jpeg")},
    )
    assert resp.status_code == 400


def test_read_label_requires_auth(client):
    resp = client.post(
        "/api/food/photo-label",
        headers={"Authorization": "Bearer not-a-real-token"},
        files={"file": ("label.jpg", b"x", "image/jpeg")},
    )
    assert resp.status_code == 401
