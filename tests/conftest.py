"""Pytest fixtures.

Tests run entirely on in-memory SQLite (no Docker / Postgres needed). Required env vars are
set before any backend import so config/encryption load cleanly.
"""
import os
from decimal import Decimal

from cryptography.fernet import Fernet

# Set env vars BEFORE importing backend.
os.environ.setdefault("FERNET_KEY", Fernet.generate_key().decode())
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("REGISTRATION_ENABLED", "true")  # tests create users via /auth/register

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api.deps import get_off_client, get_suggest_client, get_vision_client
from backend.food.off import FoodData
from backend.food.suggest_ai import (
    AiDayPlan,
    AiPlanItem,
    AiPlanMeal,
    AiSuggestion,
    AiSuggestResult,
)
from backend.main import app
from backend.persistence.database import Base, get_session
from backend.vision.estimator import EstimateItem, MacroTotal, PhotoEstimate


class _FakeOFF:
    """Fake Open Food Facts client (no network) used in tests."""

    def get_product(self, barcode: str) -> FoodData | None:
        if barcode == "0000000000000":
            return None
        return FoodData(
            name="Test Bar",
            barcode=barcode,
            per100_kcal=Decimal("400"),
            per100_protein_g=Decimal("20"),
            per100_fat_g=Decimal("10"),
            per100_carbs_g=Decimal("50"),
            serving_g=Decimal("40"),
        )

    def search(self, query: str, limit: int = 10) -> list[FoodData]:
        return [
            FoodData(
                name=f"{query} result",
                barcode="111",
                per100_kcal=Decimal("100"),
                per100_protein_g=Decimal("5"),
                per100_fat_g=Decimal("2"),
                per100_carbs_g=Decimal("15"),
                serving_g=None,
            )
        ]


class _FakeVision:
    """Fake Claude vision client (no network / no API key) used in tests."""

    def estimate(self, *, image_b64: str, media_type: str, context: str | None = None) -> PhotoEstimate:
        if context:  # re-estimate with the user's answers → confident, no questions
            return PhotoEstimate(
                items=[EstimateItem("Chicken bowl", Decimal("400"), Decimal("600"), Decimal("45"), Decimal("18"), Decimal("55"))],
                total=MacroTotal(Decimal("600"), Decimal("45"), Decimal("18"), Decimal("55")),
                confidence="high",
                questions=[],
                notes="Refined with your notes.",
            )
        return PhotoEstimate(
            items=[EstimateItem("Chicken bowl", Decimal("350"), Decimal("520"), Decimal("40"), Decimal("15"), Decimal("50"))],
            total=MacroTotal(Decimal("520"), Decimal("40"), Decimal("15"), Decimal("50")),
            confidence="medium",
            questions=["Was any oil used?"],
            notes="Approximate.",
        )


class _FakeSuggest:
    """Fake Claude suggestion client (no network / no API key) used in tests."""

    def suggest(
        self, *, remaining_kcal, protein_gap, fat_gap, carbs_gap, candidates, preferences=None
    ) -> AiSuggestResult:
        return AiSuggestResult(
            suggestions=[
                AiSuggestion(
                    name="Greek yogurt",
                    amount_g=Decimal("200"),
                    per100_kcal=Decimal("59"),
                    per100_protein_g=Decimal("10"),
                    per100_fat_g=Decimal("0.4"),
                    per100_carbs_g=Decimal("3.6"),
                    reason="High protein to close your gap.",
                )
            ],
            notes="A protein-forward option.",
        )

    def plan(
        self,
        *,
        scope,
        kcal_budget,
        protein_target,
        fat_target,
        carbs_target,
        meals,
        candidates,
        country=None,
        store=None,
        dietary_preferences=None,
        preferences=None,
        budget_daily=None,
        currency=None,
    ) -> AiDayPlan:
        # "Chicken breast" matches a saved food by name (endpoint reuses its food_id); the
        # yogurt is novel (logged inline). Mirrors the real plan() shape.
        return AiDayPlan(
            meals=[
                AiPlanMeal(
                    slot="breakfast",
                    items=[
                        AiPlanItem(
                            name="Greek yogurt",
                            amount_g=Decimal("200"),
                            per100_kcal=Decimal("59"),
                            per100_protein_g=Decimal("10"),
                            per100_fat_g=Decimal("0.4"),
                            per100_carbs_g=Decimal("3.6"),
                            reason="High protein start.",
                        )
                    ],
                ),
                AiPlanMeal(
                    slot="lunch",
                    items=[
                        AiPlanItem(
                            name="Chicken breast",
                            amount_g=Decimal("150"),
                            per100_kcal=Decimal("165"),
                            per100_protein_g=Decimal("31"),
                            per100_fat_g=Decimal("4"),
                            per100_carbs_g=Decimal("0"),
                            reason="Lean protein.",
                        )
                    ],
                ),
            ],
            notes="A balanced day.",
        )


@pytest.fixture
def engine():
    """In-memory SQLite engine for tests."""
    eng = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)  # SQLite uses create_all; Postgres uses alembic
    try:
        yield eng
    finally:
        Base.metadata.drop_all(eng)
        eng.dispose()


@pytest.fixture
def session_factory(engine):
    return sessionmaker(
        bind=engine, autoflush=False, expire_on_commit=False, class_=Session
    )


def _register(test_client: TestClient, email: str) -> TestClient:
    """Helper: POST register and set the Authorization header."""
    resp = test_client.post(
        "/api/auth/register", json={"email": email, "password": "password123"}
    )
    assert resp.status_code == 201, resp.text
    test_client.headers["Authorization"] = f"Bearer {resp.json()['access_token']}"
    return test_client


@pytest.fixture
def client(session_factory):
    """Authenticated TestClient (user-a)."""

    def _override():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = _override
    app.dependency_overrides[get_off_client] = lambda: _FakeOFF()
    app.dependency_overrides[get_vision_client] = lambda: _FakeVision()
    app.dependency_overrides[get_suggest_client] = lambda: _FakeSuggest()
    with TestClient(app) as test_client:
        _register(test_client, "user-a@example.com")
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def second_client(client):
    """A second authenticated client (different user, same DB) for isolation tests."""
    other = TestClient(app)  # shares the app + override installed by `client`
    return _register(other, "user-b@example.com")
