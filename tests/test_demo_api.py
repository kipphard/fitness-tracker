"""Public demo endpoint + AI gating + isolation."""
import pytest
from fastapi.testclient import TestClient

from backend.api import auth as auth_mod
from backend.main import app


@pytest.fixture(autouse=True)
def _clear_rate_limit():
    auth_mod._DEMO_HITS.clear()
    yield
    auth_mod._DEMO_HITS.clear()


def _demo_client(client) -> TestClient:
    """A TestClient authed as a fresh demo sandbox (reuses the app + overrides from `client`)."""
    resp = client.post("/api/auth/demo", json={})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["user"]["is_demo"] is True
    c = TestClient(app)
    c.headers["Authorization"] = f"Bearer {body['access_token']}"
    return c


def test_demo_returns_token_and_seeded_data(client):
    demo = _demo_client(client)
    today = demo.get("/api/today?tz=0")
    assert today.status_code == 200, today.text  # profile was seeded → no 404
    # Seeded history is visible.
    assert len(demo.get("/api/weight").json()) > 30
    assert len(demo.get("/api/workouts").json()) >= 10
    assert len(demo.get("/api/routines").json()) == 2


def test_two_demo_sandboxes_are_isolated(client):
    a = _demo_client(client)
    b = _demo_client(client)
    # A food only A creates must not be visible to B.
    a.post("/api/food", json={"name": "ZZ Secret Demo Food", "per100_kcal": "100"})
    assert a.get("/api/food?q=ZZ Secret").json()
    assert b.get("/api/food?q=ZZ Secret").json() == []


def test_demo_blocks_paid_ai_endpoints(client):
    demo = _demo_client(client)
    # suggest/ai + plan/ai are gated to 403 for demo users (cost money).
    assert demo.post("/api/food/suggest/ai", json={}).status_code == 403
    assert demo.post("/api/food/plan/ai", json={}).status_code == 403
    # photo too (multipart) — 403 before the vision client is even consulted.
    files = {"file": ("x.jpg", b"x", "image/jpeg")}
    assert demo.post("/api/food/photo", files=files).status_code == 403


def test_non_demo_user_not_blocked(client):
    # The fake suggest client is injected in conftest; user-a is a normal (non-demo) user.
    client.put(
        "/api/profile",
        json={"height_cm": "180", "age": 30, "gender": "male",
              "weight_kg": "80", "activity_level": "sedentary", "goal": "maintain"},
    )
    assert client.post("/api/food/suggest/ai", json={}).status_code != 403


def test_registration_can_be_disabled_but_login_and_demo_still_work(client, monkeypatch):
    from backend.config import get_settings

    monkeypatch.setattr(get_settings(), "registration_enabled", False)
    blocked = client.post(
        "/api/auth/register", json={"email": "blocked@example.com", "password": "password123"}
    )
    assert blocked.status_code == 403
    # The real login path and the public demo are unaffected.
    assert client.post(
        "/api/auth/login", json={"email": "user-a@example.com", "password": "password123"}
    ).status_code == 200
    assert client.post("/api/auth/demo", json={}).status_code == 201


def test_demo_user_counts_toward_cap(client):
    before = _demo_client(client)  # noqa: F841 - creates one demo user
    from backend.persistence import repository
    from backend.persistence.database import get_session

    # Count via a session (use the app's override factory).
    gen = app.dependency_overrides[get_session]()
    session = next(gen)
    try:
        assert repository.count_demo_users(session) >= 1
    finally:
        gen.close()
