"""Pantry endpoints (issue #5 §2): the foods the user has at home.

A simple list of saved foods; the suggestion and day-plan engines prefer these ("use what you
have first"). Adding references an existing saved food, so the macros are reusable.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from backend.api.deps import CurrentUser, SessionDep
from backend.persistence import repository
from backend.schemas import PantryItemIn, PantryItemOut

router = APIRouter(prefix="/pantry", tags=["pantry"])


@router.get("", response_model=list[PantryItemOut])
def list_pantry(session: SessionDep, user: CurrentUser) -> list[PantryItemOut]:
    return [PantryItemOut.model_validate(i) for i in repository.list_pantry(session, user.id)]


@router.post("", response_model=PantryItemOut, status_code=201)
def add_pantry(
    payload: PantryItemIn, session: SessionDep, user: CurrentUser
) -> PantryItemOut:
    """Add a saved food to the pantry (idempotent). 404 if the food isn't the user's."""
    if repository.get_food(session, payload.food_id, user.id) is None:
        raise HTTPException(status_code=404, detail="food not found")
    item = repository.add_pantry_item(session, user.id, payload.food_id, payload.note)
    session.commit()
    return PantryItemOut.model_validate(item)


@router.delete("/{food_id}", status_code=204)
def remove_pantry(food_id: uuid.UUID, session: SessionDep, user: CurrentUser) -> None:
    removed = repository.remove_pantry_by_food(session, user.id, food_id)
    session.commit()
    if not removed:
        raise HTTPException(status_code=404, detail="not in pantry")
    return None
