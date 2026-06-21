"""Auth endpoint tests (register / login / me)."""


def test_me_returns_current_user(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "user-a@example.com"


def test_duplicate_registration_conflicts(client):
    resp = client.post(
        "/api/auth/register",
        json={"email": "user-a@example.com", "password": "password123"},
    )
    assert resp.status_code == 409


def test_login_succeeds_and_rejects_bad_password(client):
    ok = client.post(
        "/api/auth/login",
        json={"email": "user-a@example.com", "password": "password123"},
    )
    assert ok.status_code == 200
    assert "access_token" in ok.json()

    bad = client.post(
        "/api/auth/login",
        json={"email": "user-a@example.com", "password": "wrong-password"},
    )
    assert bad.status_code == 401


def test_invalid_token_is_rejected(client):
    resp = client.get(
        "/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert resp.status_code == 401
