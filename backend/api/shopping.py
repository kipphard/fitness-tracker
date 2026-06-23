"""Shopping-list endpoints (issue #5 §3).

Generate a shopping list from a day plan *minus* the pantry (what you already have at home),
or add items manually; tick items off while shopping. Items are merged by name.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query

from backend.api.deps import CurrentUser, SessionDep
from backend.persistence import repository
from backend.schemas import (
    ShoppingFromPlanIn,
    ShoppingItemIn,
    ShoppingItemOut,
    ShoppingPatchIn,
)

router = APIRouter(prefix="/shopping", tags=["shopping"])


@router.get("", response_model=list[ShoppingItemOut])
def list_shopping(session: SessionDep, user: CurrentUser) -> list[ShoppingItemOut]:
    return [ShoppingItemOut.model_validate(i) for i in repository.list_shopping(session, user.id)]


@router.post("", response_model=ShoppingItemOut, status_code=201)
def add_shopping(
    payload: ShoppingItemIn, session: SessionDep, user: CurrentUser
) -> ShoppingItemOut:
    """Add (or update by name) a single item manually."""
    item = repository.upsert_shopping_item(
        session, user.id, name=payload.name, amount_g=payload.amount_g, price=payload.price
    )
    session.commit()
    return ShoppingItemOut.model_validate(item)


@router.post("/from-plan", response_model=list[ShoppingItemOut])
def add_from_plan(
    payload: ShoppingFromPlanIn, session: SessionDep, user: CurrentUser
) -> list[ShoppingItemOut]:
    """Merge a day plan's items into the shopping list, dropping anything already in the pantry.
    Items are aggregated by name (grams summed) before being saved."""
    pantry_ids = repository.pantry_food_ids(session, user.id)
    pantry_names = {
        i.food.name.strip().lower() for i in repository.list_pantry(session, user.id)
    }

    # name_key -> {name, food_id, amount_g, has_amount}
    agg: dict[str, dict] = {}
    for it in payload.items:
        if it.food_id is not None and it.food_id in pantry_ids:
            continue
        name = it.name.strip()
        key = name.lower()
        if not key or key in pantry_names:
            continue
        bucket = agg.setdefault(
            key, {"name": name, "food_id": it.food_id, "amount_g": Decimal(0), "has_amount": False}
        )
        if it.amount_g is not None:
            bucket["amount_g"] += it.amount_g
            bucket["has_amount"] = True
        if it.food_id is not None and bucket["food_id"] is None:
            bucket["food_id"] = it.food_id

    for bucket in agg.values():
        repository.upsert_shopping_item(
            session,
            user.id,
            name=bucket["name"],
            amount_g=bucket["amount_g"] if bucket["has_amount"] else None,
            food_id=bucket["food_id"],
        )
    session.commit()
    return [ShoppingItemOut.model_validate(i) for i in repository.list_shopping(session, user.id)]


@router.patch("/{item_id}", response_model=ShoppingItemOut)
def patch_shopping(
    item_id: uuid.UUID, payload: ShoppingPatchIn, session: SessionDep, user: CurrentUser
) -> ShoppingItemOut:
    """Tick an item off and/or set its estimated price (only the sent fields are applied)."""
    fields = payload.model_dump(exclude_unset=True)
    item = repository.update_shopping_item(session, item_id, user.id, **fields)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    session.commit()
    return ShoppingItemOut.model_validate(item)


@router.delete("/{item_id}", status_code=204)
def remove_shopping(item_id: uuid.UUID, session: SessionDep, user: CurrentUser) -> None:
    removed = repository.remove_shopping_item(session, item_id, user.id)
    session.commit()
    if not removed:
        raise HTTPException(status_code=404, detail="item not found")
    return None


@router.delete("", status_code=204)
def clear_shopping(
    session: SessionDep,
    user: CurrentUser,
    checked: bool = Query(default=False, description="clear only checked items when true"),
) -> None:
    """Clear the whole list, or only the checked items with ?checked=true."""
    repository.clear_shopping(session, user.id, checked_only=checked)
    session.commit()
    return None
