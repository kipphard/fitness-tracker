"""Photo-estimation endpoint tests (Claude vision is faked in conftest)."""
from decimal import Decimal


def test_photo_estimate_returns_items_and_questions(client):
    resp = client.post(
        "/api/food/photo",
        files={"file": ("meal.jpg", b"\xff\xd8\xff\xe0fake-jpeg-bytes", "image/jpeg")},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["confidence"] == "medium"
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "Chicken bowl"
    assert data["questions"] == ["Was any oil used?"]
    assert Decimal(data["total"]["kcal"]) == Decimal("520")


def test_photo_estimate_with_context_refines(client):
    resp = client.post(
        "/api/food/photo",
        files={"file": ("meal.jpg", b"fake-image", "image/jpeg")},
        data={"context": "no oil, about 400 g"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["confidence"] == "high"
    assert data["questions"] == []
    assert Decimal(data["total"]["kcal"]) == Decimal("600")


def test_photo_estimate_rejects_non_image(client):
    resp = client.post(
        "/api/food/photo",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 415


def test_photo_requires_auth(client):
    resp = client.post(
        "/api/food/photo",
        headers={"Authorization": "Bearer not-a-real-token"},
        files={"file": ("m.jpg", b"x", "image/jpeg")},
    )
    assert resp.status_code == 401
