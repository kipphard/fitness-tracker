"""User-defined meal slots: read and replace the ordered per-user slot list.

The list is persisted on the user's Settings row (``meal_slots``). GET returns the effective
list (built-ins always present); PUT replaces it wholesale with a normalized list (see
``backend.food.slots``)."""
from __future__ import annotations

from fastapi import APIRouter

from backend.api.deps import CurrentUser, SessionDep
from backend.food.slots import normalize_slots, slot_out_list
from backend.persistence import repository
from backend.schemas import MealSlotOut, MealSlotsIn

router = APIRouter(prefix="/meal-slots", tags=["meal-slots"])


def _stored(session: SessionDep, user_id) -> list | None:
    settings = repository.get_settings(session, user_id)
    return settings.meal_slots if settings is not None else None


@router.get("", response_model=list[MealSlotOut])
def list_slots(session: SessionDep, user: CurrentUser) -> list[MealSlotOut]:
    return [MealSlotOut(**s) for s in slot_out_list(_stored(session, user.id))]


@router.put("", response_model=list[MealSlotOut])
def replace_slots(
    payload: MealSlotsIn, session: SessionDep, user: CurrentUser
) -> list[MealSlotOut]:
    normalized = normalize_slots(payload.slots)
    repository.upsert_settings(session, user.id, meal_slots=normalized)
    session.commit()
    return [MealSlotOut(**s) for s in slot_out_list(normalized)]
