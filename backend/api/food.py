"""Food endpoints: saved foods, custom foods, Open Food Facts (Phase 4), and the Claude
vision photo estimator (Phase 5)."""
from __future__ import annotations

import base64
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.api.deps import (
    CurrentUser,
    OffClientDep,
    SessionDep,
    SuggestClientDep,
    VisionClientDep,
)
from backend.api.today import compute_today
from backend.config import get_settings
from backend.food import suggest as suggest_engine
from backend.persistence import repository
from backend.persistence.models import FoodSource, User
from backend.schemas import (
    FoodDataOut,
    FoodIn,
    FoodOut,
    PhotoEstimateOut,
    SuggestAiIn,
    SuggestIn,
    SuggestionOut,
    SuggestOut,
)

router = APIRouter(prefix="/food", tags=["food"])

_MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MB
_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


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


@router.post("/photo", response_model=PhotoEstimateOut)
def estimate_photo(
    user: CurrentUser,  # resolved first, so unauthenticated requests 401 before the 503 check
    vision: VisionClientDep,
    file: UploadFile = File(...),
    context: str | None = Form(default=None),
) -> PhotoEstimateOut:
    """Estimate a meal's items + macros from a photo via Claude vision. The optional `context`
    carries the user's answers to clarifying questions for a refined re-estimate."""
    media_type = (file.content_type or "image/jpeg").split(";")[0].strip().lower()
    if media_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="unsupported image type")
    data = file.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="empty file")
    if len(data) > _MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="image too large (max 8 MB)")

    image_b64 = base64.standard_b64encode(data).decode()
    try:
        estimate = vision.estimate(
            image_b64=image_b64, media_type=media_type, context=context
        )
    except Exception as exc:  # noqa: BLE001 - upstream/model failure
        raise HTTPException(status_code=502, detail="photo estimation failed") from exc
    return PhotoEstimateOut.model_validate(estimate)


# --- fill remaining calories (issue #5, section 1) ---


def _suggest_context(session: SessionDep, user: User, day: date, tz: int):
    """Shared inputs for both suggestion paths: the day's remaining kcal + macro gaps (vs.
    target) and the candidate food pool (recents first, then the rest of the catalogue)."""
    today = compute_today(session, user, day, tz)
    remaining = today.remaining_kcal
    protein_gap = today.macros.protein_g - today.consumed.protein_g
    fat_gap = today.macros.fat_g - today.consumed.fat_g
    carbs_gap = today.macros.carbs_g - today.consumed.carbs_g

    recents = repository.recent_foods(session, user.id, limit=30)
    seen = {f.id for f in recents}
    pool = recents + [
        f for f in repository.list_foods(session, user.id, limit=200) if f.id not in seen
    ]
    candidates = [
        suggest_engine.Candidate(
            food_id=f.id,
            name=f.name,
            per100_kcal=f.per100_kcal,
            per100_protein_g=f.per100_protein_g,
            per100_fat_g=f.per100_fat_g,
            per100_carbs_g=f.per100_carbs_g,
        )
        for f in pool
    ]
    return today.date, remaining, protein_gap, fat_gap, carbs_gap, candidates


@router.post("/suggest", response_model=SuggestOut)
def suggest_fill(payload: SuggestIn, session: SessionDep, user: CurrentUser) -> SuggestOut:
    """Rule-based suggestions: foods + portions from the user's catalogue that fill the day's
    remaining calories, ranked by macro-gap fit. Always available (no API key needed)."""
    day = payload.date or date.today()
    on, remaining, pg, fg, cg, candidates = _suggest_context(session, user, day, payload.tz)
    suggestions = suggest_engine.suggest_foods(
        remaining_kcal=remaining,
        protein_gap=pg,
        fat_gap=fg,
        carbs_gap=cg,
        candidates=candidates,
    )
    return SuggestOut(
        date=on,
        remaining_kcal=remaining,
        protein_gap_g=max(pg, Decimal(0)),
        fat_gap_g=max(fg, Decimal(0)),
        carbs_gap_g=max(cg, Decimal(0)),
        suggestions=[SuggestionOut.model_validate(s) for s in suggestions],
        ai_available=get_settings().anthropic_configured,
        source="rule",
    )


@router.post("/suggest/ai", response_model=SuggestOut)
def suggest_fill_ai(
    payload: SuggestAiIn,
    session: SessionDep,
    user: CurrentUser,
    client: SuggestClientDep,
) -> SuggestOut:
    """AI-assisted suggestions via Claude. 503 until ANTHROPIC_API_KEY is set (issue #2);
    falls through to an empty list when the budget is already met."""
    day = payload.date or date.today()
    on, remaining, pg, fg, cg, candidates = _suggest_context(session, user, day, payload.tz)
    pg, fg, cg = max(pg, Decimal(0)), max(fg, Decimal(0)), max(cg, Decimal(0))

    suggestions: list[suggest_engine.Suggestion] = []
    notes = ""
    if remaining >= suggest_engine.MIN_GAP_KCAL:
        try:
            result = client.suggest(
                remaining_kcal=remaining,
                protein_gap=pg,
                fat_gap=fg,
                carbs_gap=cg,
                candidates=candidates,
                preferences=payload.preferences,
            )
        except Exception as exc:  # noqa: BLE001 - upstream/model failure
            raise HTTPException(status_code=502, detail="suggestion failed") from exc
        notes = result.notes
        by_name = {c.name.strip().lower(): c for c in candidates}
        for s in result.suggestions:
            # Reuse a saved food (authoritative per-100g + food_id) when the name matches.
            match = by_name.get(s.name.strip().lower())
            if match is not None:
                suggestions.append(
                    suggest_engine.build_suggestion(
                        food_id=match.food_id,
                        name=match.name,
                        amount_g=s.amount_g,
                        per100_kcal=match.per100_kcal,
                        per100_protein_g=match.per100_protein_g,
                        per100_fat_g=match.per100_fat_g,
                        per100_carbs_g=match.per100_carbs_g,
                        reason=s.reason,
                    )
                )
            else:
                suggestions.append(
                    suggest_engine.build_suggestion(
                        food_id=None,
                        name=s.name,
                        amount_g=s.amount_g,
                        per100_kcal=s.per100_kcal,
                        per100_protein_g=s.per100_protein_g,
                        per100_fat_g=s.per100_fat_g,
                        per100_carbs_g=s.per100_carbs_g,
                        reason=s.reason,
                    )
                )

    return SuggestOut(
        date=on,
        remaining_kcal=remaining,
        protein_gap_g=pg,
        fat_gap_g=fg,
        carbs_gap_g=cg,
        suggestions=[SuggestionOut.model_validate(s) for s in suggestions],
        ai_available=True,
        source="ai",
        notes=notes,
    )
