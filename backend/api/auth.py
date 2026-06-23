"""Auth endpoints: register, login, current user, and the public live-demo sandbox."""
from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, HTTPException, Request

from backend.api.deps import CurrentUser, SessionDep
from backend.auth.security import create_access_token, hash_password, verify_password
from backend.config import get_settings
from backend.demo.seed import seed_demo_for_user
from backend.persistence import repository
from backend.persistence.models import User
from backend.schemas import LoginIn, RegisterIn, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

# In-memory per-IP rate-limit state for the demo endpoint (single-process uvicorn). Maps a
# client IP to recent request timestamps; pruned on each call.
_DEMO_HITS: dict[str, list[float]] = {}


def _token(user: User) -> TokenOut:
    return TokenOut(
        access_token=create_access_token(str(user.id)),
        user=UserOut.model_validate(user),
    )


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _rate_ok(ip: str, limit: int, window: float = 3600.0) -> bool:
    now = time.time()
    hits = [t for t in _DEMO_HITS.get(ip, []) if now - t < window]
    if len(hits) >= limit:
        _DEMO_HITS[ip] = hits
        return False
    hits.append(now)
    _DEMO_HITS[ip] = hits
    return True


@router.post("/register", response_model=TokenOut, status_code=201)
def register(payload: RegisterIn, session: SessionDep) -> TokenOut:
    if not get_settings().registration_enabled:
        raise HTTPException(status_code=403, detail="registration is closed")
    email = payload.email.lower()
    if repository.get_user_by_email(session, email) is not None:
        raise HTTPException(status_code=409, detail="email already registered")
    user = repository.create_user(
        session, email=email, password_hash=hash_password(payload.password)
    )
    session.commit()
    return _token(user)


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, session: SessionDep) -> TokenOut:
    user = repository.get_user_by_email(session, payload.email.lower())
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="account disabled")
    return _token(user)


@router.post("/demo", response_model=TokenOut, status_code=201)
def demo(request: Request, session: SessionDep) -> TokenOut:
    """Spin up a private, seeded, auto-expiring demo sandbox and return a token for it. Public
    (no credentials). Each call creates a fresh is_demo user with its own isolated data."""
    settings = get_settings()
    if not settings.demo_enabled:
        raise HTTPException(status_code=403, detail="demo is disabled")
    if not _rate_ok(_client_ip(request), settings.demo_per_ip_per_hour):
        raise HTTPException(status_code=429, detail="too many demo sessions — try again later")
    if repository.count_demo_users(session) >= settings.demo_max_active:
        raise HTTPException(status_code=429, detail="demo is at capacity — try again later")

    user = repository.create_user(
        session,
        email=f"demo+{uuid.uuid4().hex}@demo.invalid",
        password_hash=hash_password(uuid.uuid4().hex),
        is_demo=True,
    )
    seed_demo_for_user(session, user.id)  # commits
    return _token(user)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
