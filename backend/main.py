"""FastAPI application entry point."""
from __future__ import annotations

from fastapi import FastAPI

from backend.api import (
    auth,
    calories,
    diary,
    exercises,
    food,
    health,
    macros,
    measurements,
    pantry,
    profile,
    routines,
    settings,
    shopping,
    steps,
    today,
    trends,
    weight,
    workouts,
)
from backend.config import get_settings

app_settings = get_settings()

# Data routers live under /api so nginx can serve the SPA at / on the same origin.
# Docs move under /api too; /health stays at the root for ops/healthchecks.
app = FastAPI(
    title=app_settings.app_name,
    summary="Self-hosted fitness & nutrition tracker",
    version="0.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

API = "/api"
app.include_router(health.router)  # stays at /health, public
app.include_router(auth.router, prefix=API)  # register/login public; /me authed
app.include_router(profile.router, prefix=API)
app.include_router(settings.router, prefix=API)
app.include_router(calories.router, prefix=API)
app.include_router(weight.router, prefix=API)
app.include_router(macros.router, prefix=API)
app.include_router(food.router, prefix=API)
app.include_router(pantry.router, prefix=API)
app.include_router(shopping.router, prefix=API)
app.include_router(diary.router, prefix=API)
app.include_router(steps.router, prefix=API)
app.include_router(today.router, prefix=API)
app.include_router(exercises.router, prefix=API)
app.include_router(routines.router, prefix=API)
app.include_router(workouts.router, prefix=API)
app.include_router(measurements.router, prefix=API)
app.include_router(trends.router, prefix=API)


@app.get("/", tags=["root"])
def root() -> dict:
    return {"name": app_settings.app_name, "docs": "/api/docs"}
