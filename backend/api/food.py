"""Food endpoints: saved foods, custom foods, Open Food Facts (Phase 4), and the Claude
vision photo estimator (Phase 5)."""
from __future__ import annotations

import base64
import uuid
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
from backend.food import plan as plan_engine
from backend.food import suggest as suggest_engine
from backend.persistence import repository
from backend.persistence.models import Food, FoodSource, MealSlot, User
from backend.schemas import (
    BackfillOut,
    FoodDataOut,
    FoodIn,
    FoodOut,
    FoodUpdateIn,
    PhotoEstimateOut,
    PlanIn,
    PlanMealOut,
    PlanOut,
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


def _suggest_context(
    session: SessionDep,
    user: User,
    day: date,
    tz: int,
    slot=None,
    exclude_ids: set | None = None,
):
    """Shared inputs for both suggestion paths: the day's remaining kcal + macro gaps (vs.
    target) and the candidate food pool (recents first, then the rest of the catalogue),
    annotated with slot affinity and with excluded/duplicate foods removed."""
    exclude_ids = exclude_ids or set()
    today = compute_today(session, user, day, tz)
    remaining = today.remaining_kcal
    protein_gap = today.macros.protein_g - today.consumed.protein_g
    fat_gap = today.macros.fat_g - today.consumed.fat_g
    carbs_gap = today.macros.carbs_g - today.consumed.carbs_g

    affinity = repository.food_slot_counts(session, user.id, slot) if slot else {}
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
            serving_g=f.serving_g,
            slot_affinity=affinity.get(f.id, 0),
        )
        for f in pool
        if f.id not in exclude_ids
    ]
    candidates = suggest_engine.dedup_candidates(candidates)
    return today.date, remaining, protein_gap, fat_gap, carbs_gap, candidates


@router.post("/suggest", response_model=SuggestOut)
def suggest_fill(payload: SuggestIn, session: SessionDep, user: CurrentUser) -> SuggestOut:
    """Rule-based suggestions: foods + portions from the user's catalogue that fill the day's
    remaining calories, ranked by macro-gap fit. Always available (no API key needed).

    ``exclude_food_ids`` regenerates around foods already shown; ``count``=1 with
    ``target_kcal`` swaps a single item for an equivalent-size alternative; ``slot`` biases
    picks toward that meal."""
    day = payload.date or date.today()
    on, remaining, pg, fg, cg, candidates = _suggest_context(
        session, user, day, payload.tz, payload.slot, set(payload.exclude_food_ids)
    )
    suggestions = suggest_engine.suggest_basket(
        remaining_kcal=payload.target_kcal or remaining,
        protein_gap=pg,
        fat_gap=fg,
        carbs_gap=cg,
        candidates=candidates,
        max_items=payload.count or suggest_engine.MAX_BASKET_ITEMS,
        slot=payload.slot.value if payload.slot else None,
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
    on, remaining, pg, fg, cg, candidates = _suggest_context(
        session, user, day, payload.tz, payload.slot, set(payload.exclude_food_ids)
    )
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


# --- generate a day's meal plan (issue #5, section 2) ---


def _plan_basis(today, scope: str) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """The kcal budget + macro targets the plan should fill, given the scope.

    ``full_day`` aims at the whole day's eating budget + macro targets (a fresh blueprint,
    ignoring what's already logged); ``remaining`` aims only at what's left after today's logged
    food (gaps, floored at 0)."""
    if scope == "remaining":
        return (
            max(today.remaining_kcal, Decimal(0)),
            max(today.macros.protein_g - today.consumed.protein_g, Decimal(0)),
            max(today.macros.fat_g - today.consumed.fat_g, Decimal(0)),
            max(today.macros.carbs_g - today.consumed.carbs_g, Decimal(0)),
        )
    # full_day: remaining + consumed reconstructs the day's whole eating budget.
    return (
        today.remaining_kcal + today.consumed.kcal,
        today.macros.protein_g,
        today.macros.fat_g,
        today.macros.carbs_g,
    )


def _plan_candidate_pool(session: SessionDep, user: User) -> list[Food]:
    """The user's food catalogue for planning: recents first, then the rest of the catalogue."""
    recents = repository.recent_foods(session, user.id, limit=30)
    seen = {f.id for f in recents}
    return recents + [
        f for f in repository.list_foods(session, user.id, limit=200) if f.id not in seen
    ]


def _to_candidate(f: Food, affinity: int = 0) -> "suggest_engine.Candidate":
    return suggest_engine.Candidate(
        food_id=f.id,
        name=f.name,
        per100_kcal=f.per100_kcal,
        per100_protein_g=f.per100_protein_g,
        per100_fat_g=f.per100_fat_g,
        per100_carbs_g=f.per100_carbs_g,
        serving_g=f.serving_g,
        slot_affinity=affinity,
    )


def _build_plan_out(
    *,
    day: date,
    scope: str,
    target_kcal: Decimal,
    planned: list[plan_engine.PlannedMeal],
    source: str,
    ai_available: bool,
    notes: str,
) -> PlanOut:
    """Package planned meals into a PlanOut, computing per-slot and whole-day totals."""
    meals_out: list[PlanMealOut] = []
    tot_k = tot_p = tot_f = tot_c = Decimal(0)
    for pm in planned:
        s_k = sum((s.kcal for s in pm.suggestions), Decimal(0))
        s_p = sum((s.protein_g for s in pm.suggestions), Decimal(0))
        s_f = sum((s.fat_g for s in pm.suggestions), Decimal(0))
        s_c = sum((s.carbs_g for s in pm.suggestions), Decimal(0))
        tot_k, tot_p, tot_f, tot_c = tot_k + s_k, tot_p + s_p, tot_f + s_f, tot_c + s_c
        meals_out.append(
            PlanMealOut(
                slot=MealSlot(pm.slot),
                suggestions=[SuggestionOut.model_validate(s) for s in pm.suggestions],
                kcal=s_k,
                protein_g=s_p,
                fat_g=s_f,
                carbs_g=s_c,
            )
        )
    return PlanOut(
        date=day,
        scope=scope,
        target_kcal=target_kcal,
        meals=meals_out,
        planned_kcal=tot_k,
        planned_protein_g=tot_p,
        planned_fat_g=tot_f,
        planned_carbs_g=tot_c,
        ai_available=ai_available,
        source=source,
        notes=notes,
    )


@router.post("/plan", response_model=PlanOut)
def plan_rule(payload: PlanIn, session: SessionDep, user: CurrentUser) -> PlanOut:
    """Rule-based day plan: split the (whole-day or remaining) target across meals and fill each
    from the user's catalogue, slot affinity aware. Always available (no API key needed)."""
    day = payload.date or date.today()
    today = compute_today(session, user, day, payload.tz)
    kcal, protein, fat, carbs = _plan_basis(today, payload.scope)

    foods = _plan_candidate_pool(session, user)
    by_slot: dict[str, list[suggest_engine.Candidate]] = {}
    for slot, _pct in plan_engine.meal_split(payload.meals):
        affinity = repository.food_slot_counts(session, user.id, MealSlot(slot))
        by_slot[slot] = suggest_engine.dedup_candidates(
            [_to_candidate(f, affinity.get(f.id, 0)) for f in foods]
        )

    planned = plan_engine.plan_day(
        kcal_budget=kcal,
        protein_target=protein,
        fat_target=fat,
        carbs_target=carbs,
        candidates_by_slot=by_slot,
        meals=payload.meals,
    )
    return _build_plan_out(
        day=today.date,
        scope=payload.scope,
        target_kcal=kcal,
        planned=planned,
        source="rule",
        ai_available=get_settings().anthropic_configured,
        notes="",
    )


@router.post("/plan/ai", response_model=PlanOut)
def plan_ai(
    payload: PlanIn,
    session: SessionDep,
    user: CurrentUser,
    client: SuggestClientDep,
) -> PlanOut:
    """AI day plan via Claude: store/country-aware realistic products that hit the target. 503
    until ANTHROPIC_API_KEY is set (issue #2); the rule path above stays available regardless."""
    day = payload.date or date.today()
    today = compute_today(session, user, day, payload.tz)
    kcal, protein, fat, carbs = _plan_basis(today, payload.scope)

    foods = _plan_candidate_pool(session, user)
    candidates = suggest_engine.dedup_candidates([_to_candidate(f) for f in foods])
    settings = repository.get_settings(session, user.id)

    try:
        result = client.plan(
            scope=payload.scope,
            kcal_budget=kcal,
            protein_target=protein,
            fat_target=fat,
            carbs_target=carbs,
            meals=payload.meals,
            candidates=candidates,
            country=settings.country if settings else None,
            store=settings.store if settings else None,
            dietary_preferences=settings.dietary_preferences if settings else None,
            preferences=payload.preferences,
        )
    except Exception as exc:  # noqa: BLE001 - upstream/model failure
        raise HTTPException(status_code=502, detail="plan generation failed") from exc

    by_name = {c.name.strip().lower(): c for c in candidates}
    planned: list[plan_engine.PlannedMeal] = []
    for m in result.meals:
        suggestions: list[suggest_engine.Suggestion] = []
        for it in m.items:
            # Reuse a saved food (authoritative per-100g + food_id) when the name matches.
            match = by_name.get(it.name.strip().lower())
            if match is not None:
                suggestions.append(
                    suggest_engine.build_suggestion(
                        food_id=match.food_id,
                        name=match.name,
                        amount_g=it.amount_g,
                        per100_kcal=match.per100_kcal,
                        per100_protein_g=match.per100_protein_g,
                        per100_fat_g=match.per100_fat_g,
                        per100_carbs_g=match.per100_carbs_g,
                        reason=it.reason,
                    )
                )
            else:
                suggestions.append(
                    suggest_engine.build_suggestion(
                        food_id=None,
                        name=it.name,
                        amount_g=it.amount_g,
                        per100_kcal=it.per100_kcal,
                        per100_protein_g=it.per100_protein_g,
                        per100_fat_g=it.per100_fat_g,
                        per100_carbs_g=it.per100_carbs_g,
                        reason=it.reason,
                    )
                )
        planned.append(plan_engine.PlannedMeal(slot=m.slot, suggestions=suggestions))

    return _build_plan_out(
        day=today.date,
        scope=payload.scope,
        target_kcal=kcal,
        planned=planned,
        source="ai",
        ai_available=True,
        notes=result.notes,
    )


# --- food maintenance (serving sizes) ---


@router.post("/backfill-servings", response_model=BackfillOut)
def backfill_servings(
    session: SessionDep, user: CurrentUser, off: OffClientDep
) -> BackfillOut:
    """Re-fetch serving sizes from Open Food Facts for the user's OFF foods that lack one, so
    suggestions can size realistic portions. Capped and best-effort (skips on lookup failure)."""
    missing = [
        f
        for f in repository.list_foods(session, user.id, limit=500)
        if f.serving_g is None and f.source == FoodSource.off and f.barcode
    ]
    checked = updated = 0
    for f in missing[:50]:
        checked += 1
        try:
            data = off.get_product(f.barcode)
        except Exception:  # noqa: BLE001 - skip transient/network failures
            continue
        if data is not None and data.serving_g:
            repository.update_food(session, f, serving_g=data.serving_g)
            updated += 1
    if updated:
        session.commit()
    return BackfillOut(checked=checked, updated=updated)


@router.patch("/{food_id}", response_model=FoodOut)
def edit_food(
    food_id: uuid.UUID, payload: FoodUpdateIn, session: SessionDep, user: CurrentUser
) -> FoodOut:
    """Update a saved food — chiefly to set a serving size after the fact. Only the provided
    fields change; previously logged diary entries keep their snapshot macros."""
    food = repository.get_food(session, food_id, user.id)
    if food is None:
        raise HTTPException(status_code=404, detail="food not found")
    fields = payload.model_dump(exclude_unset=True)
    if fields:
        repository.update_food(session, food, **fields)
        session.commit()
    return FoodOut.model_validate(food)
