"""Query helpers. Everything is user-scoped."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.persistence.models import Profile, Settings, User


# --- users ---

def create_user(session: Session, *, email: str, password_hash: str) -> User:
    user = User(email=email, password_hash=password_hash)
    session.add(user)
    session.flush()
    return user


def get_user(session: Session, user_id: uuid.UUID) -> User | None:
    return session.get(User, user_id)


def get_user_by_email(session: Session, email: str) -> User | None:
    return session.scalar(select(User).where(User.email == email))


# --- profile (1:1) ---

def get_profile(session: Session, user_id: uuid.UUID) -> Profile | None:
    return session.scalar(select(Profile).where(Profile.user_id == user_id))


def upsert_profile(session: Session, user_id: uuid.UUID, **fields: Any) -> Profile:
    profile = get_profile(session, user_id)
    if profile is None:
        profile = Profile(user_id=user_id, **fields)
        session.add(profile)
    else:
        for key, value in fields.items():
            setattr(profile, key, value)
    session.flush()
    return profile


# --- settings (1:1) ---

def get_settings(session: Session, user_id: uuid.UUID) -> Settings | None:
    return session.scalar(select(Settings).where(Settings.user_id == user_id))


def upsert_settings(session: Session, user_id: uuid.UUID, **fields: Any) -> Settings:
    settings = get_settings(session, user_id)
    if settings is None:
        settings = Settings(user_id=user_id, **fields)
        session.add(settings)
    else:
        for key, value in fields.items():
            setattr(settings, key, value)
    session.flush()
    return settings
