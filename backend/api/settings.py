"""Per-user settings: language + unit preferences."""
from __future__ import annotations

from fastapi import APIRouter

from backend.api.deps import CurrentUser, SessionDep
from backend.persistence import repository
from backend.persistence.models import Settings
from backend.schemas import SettingsIn, SettingsOut

router = APIRouter(prefix="/settings", tags=["settings"])


def _ensure(session: SessionDep, user_id) -> Settings:
    """Return the user's settings row, creating it with column defaults if absent."""
    settings = repository.get_settings(session, user_id)
    if settings is None:
        settings = repository.upsert_settings(session, user_id)
    return settings


@router.get("", response_model=SettingsOut)
def read_settings(session: SessionDep, user: CurrentUser) -> SettingsOut:
    settings = _ensure(session, user.id)
    session.commit()
    return SettingsOut.model_validate(settings)


@router.put("", response_model=SettingsOut)
def update_settings(
    payload: SettingsIn, session: SessionDep, user: CurrentUser
) -> SettingsOut:
    fields = payload.model_dump(exclude_none=True)
    settings = repository.upsert_settings(session, user.id, **fields)
    session.commit()
    return SettingsOut.model_validate(settings)
