"""Shared FastAPI dependencies."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.auth.security import decode_token
from backend.food.off import OpenFoodFactsClient
from backend.persistence import repository
from backend.persistence.database import get_session
from backend.persistence.models import User

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


def get_off_client() -> OpenFoodFactsClient:
    """Open Food Facts client. Overridden in tests with a fake (no network)."""
    return OpenFoodFactsClient()


OffClientDep = Annotated[OpenFoodFactsClient, Depends(get_off_client)]
