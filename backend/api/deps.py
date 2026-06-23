"""Shared FastAPI dependencies."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.auth.security import decode_token
from backend.config import get_settings
from backend.food.off import OpenFoodFactsClient
from backend.persistence import repository
from backend.persistence.database import get_session
from backend.food.suggest_ai import AnthropicSuggestClient
from backend.persistence.models import User
from backend.vision.estimator import AnthropicVisionClient

SessionDep = Annotated[Session, Depends(get_session)]

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    subject = decode_token(credentials.credentials)
    if subject is None:
        raise HTTPException(status_code=401, detail="invalid or expired token")
    try:
        user_id = uuid.UUID(subject)
    except ValueError:
        raise HTTPException(status_code=401, detail="invalid token subject") from None
    user = repository.get_user(session, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="user not found")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def block_in_demo(user: CurrentUser) -> None:
    """Reject the request for demo users — used to gate paid (Anthropic) endpoints. Demo users
    can do everything else; this only blocks features that would cost money."""
    if user.is_demo:
        raise HTTPException(status_code=403, detail="disabled in demo")


def get_off_client() -> OpenFoodFactsClient:
    """Open Food Facts client. Overridden in tests with a fake (no network)."""
    return OpenFoodFactsClient()


OffClientDep = Annotated[OpenFoodFactsClient, Depends(get_off_client)]


def get_vision_client() -> AnthropicVisionClient:
    """Claude vision client for photo estimation. 503 if no API key; faked in tests."""
    settings = get_settings()
    if not settings.anthropic_configured or settings.anthropic_api_key is None:
        raise HTTPException(
            status_code=503,
            detail="photo estimation is not configured (set ANTHROPIC_API_KEY).",
        )
    return AnthropicVisionClient(
        api_key=settings.anthropic_api_key, model=settings.anthropic_model
    )


VisionClientDep = Annotated[AnthropicVisionClient, Depends(get_vision_client)]


def get_suggest_client() -> AnthropicSuggestClient:
    """Claude client for AI meal suggestions. 503 if no API key; faked in tests."""
    settings = get_settings()
    if not settings.anthropic_configured or settings.anthropic_api_key is None:
        raise HTTPException(
            status_code=503,
            detail="AI suggestions are not configured (set ANTHROPIC_API_KEY).",
        )
    return AnthropicSuggestClient(
        api_key=settings.anthropic_api_key, model=settings.anthropic_model
    )


SuggestClientDep = Annotated[AnthropicSuggestClient, Depends(get_suggest_client)]
