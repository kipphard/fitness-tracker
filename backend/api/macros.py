"""Macro preference endpoints (Phase 3): protein/fat grams per kg of bodyweight."""
from __future__ import annotations

from fastapi import APIRouter

from backend.api.deps import CurrentUser, SessionDep
from backend.persistence import repository
from backend.persistence.models import MacroTarget
from backend.schemas import MacroPrefIn, MacroPrefOut

router = APIRouter(prefix="/macros", tags=["macros"])


def _ensure(session: SessionDep, user_id) -> MacroTarget:
    """The user's macro prefs, creating them with column defaults if absent."""
    macro = repository.get_macro_target(session, user_id)
    if macro is None:
        macro = repository.upsert_macro_target(session, user_id)
    return macro


@router.get("", response_model=MacroPrefOut)
def read_macros(session: SessionDep, user: CurrentUser) -> MacroPrefOut:
    macro = _ensure(session, user.id)
    session.commit()
    return MacroPrefOut.model_validate(macro)


@router.put("", response_model=MacroPrefOut)
def update_macros(
    payload: MacroPrefIn, session: SessionDep, user: CurrentUser
) -> MacroPrefOut:
    fields = payload.model_dump(exclude_none=True)
    macro = repository.upsert_macro_target(session, user.id, **fields)
    session.commit()
    return MacroPrefOut.model_validate(macro)
