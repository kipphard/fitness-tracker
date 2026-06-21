"""Food catalogue endpoints (Phase 4): saved foods, custom foods, and Open Food Facts."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.api.deps import CurrentUser, OffClientDep, SessionDep
from backend.persistence import repository
from backend.persistence.models import FoodSource
from backend.schemas import FoodDataOut, FoodIn, FoodOut

router = APIRouter(prefix="/food", tags=["food"])


@router.get("", response_model=list[FoodOut])
def search_saved(q: str, session: SessionDep, user: CurrentUser) -> list[FoodOut]:
    """Search the user's saved foods (custom + previously cached) by name."""
    if not q.strip():
        return []
    foods = repository.search_foods(session, user.id, q.strip())
    return [FoodOut.model_validate(f) for f in foods]


@router.post("", response_model=FoodOut, status_code=201)
def create_custom_food(
    payload: FoodIn, session: SessionDep, user: CurrentUser
) -> FoodOut:
    food = repository.create_food(
        session,
        user.id,
        source=FoodSource.custom,
        name=payload.name,
        barcode=payload.barcode,
        per100_kcal=payload.per100_kcal,
        per100_protein_g=payload.per100_protein_g,
        per100_fat_g=payload.per100_fat_g,
        per100_carbs_g=payload.per100_carbs_g,
        serving_g=payload.serving_g,
    )
    session.commit()
    return FoodOut.model_validate(food)


@router.get("/search", response_model=list[FoodDataOut])
def search_off(q: str, off: OffClientDep, user: CurrentUser) -> list[FoodDataOut]:
    """Online Open Food Facts text search (results are transient until logged)."""
    if not q.strip():
        return []
    try:
        results = off.search(q.strip())
    except Exception as exc:  # noqa: BLE001 - upstream/network failure
        raise HTTPException(status_code=502, detail="Open Food Facts search failed") from exc
    return [FoodDataOut.model_validate(r) for r in results]


@router.get("/barcode/{barcode}", response_model=FoodOut)
def lookup_barcode(
    barcode: str, off: OffClientDep, session: SessionDep, user: CurrentUser
) -> FoodOut:
    """Barcode lookup: returns the cached food if seen before, else fetches from OFF and
    caches it for the user."""
    existing = repository.get_food_by_barcode(session, user.id, barcode)
    if existing is not None:
        return FoodOut.model_validate(existing)
    try:
        data = off.get_product(barcode)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail="Open Food Facts lookup failed") from exc
    if data is None:
        raise HTTPException(status_code=404, detail="product not found")
    food = repository.create_food(
        session,
        user.id,
        source=FoodSource.off,
        name=data.name,
        barcode=data.barcode or barcode,
        per100_kcal=data.per100_kcal,
        per100_protein_g=data.per100_protein_g,
        per100_fat_g=data.per100_fat_g,
        per100_carbs_g=data.per100_carbs_g,
        serving_g=data.serving_g,
    )
    session.commit()
    return FoodOut.model_validate(food)
