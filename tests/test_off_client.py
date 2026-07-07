"""Unit tests for the Open Food Facts client's network mapping (no real network).

The API-level tests use a fake OFF client; these cover the real client's URL/params and
response mapping, including the modern-search → legacy fallback.
"""
from decimal import Decimal

import httpx

from backend.food import off
from backend.food.off import OpenFoodFactsClient

_HIT = {
    "code": "3017620422003",
    "product_name": "Nutella",
    "nutriments": {
        "energy-kcal_100g": 539,
        "proteins_100g": 6.3,
        "fat_100g": 30.9,
        "carbohydrates_100g": 57.5,
    },
}


class _Resp:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:  # pragma: no cover - trivial
        pass

    def json(self) -> dict:
        return self._payload


def test_search_uses_modern_endpoint_and_maps_hits(monkeypatch):
    captured: dict = {}

    def fake_get(url, params=None, timeout=None, headers=None):
        captured["url"] = url
        captured["params"] = params
        captured["headers"] = headers
        return _Resp({"hits": [_HIT]})

    monkeypatch.setattr(off.httpx, "get", fake_get)
    results = OpenFoodFactsClient().search("nutella")

    assert captured["url"] == "https://search.openfoodfacts.org/search"
    assert captured["params"]["q"] == "nutella"
    assert captured["headers"]["User-Agent"].startswith("fitness-tracker/")
    assert len(results) == 1
    assert results[0].name == "Nutella"
    assert results[0].per100_kcal == Decimal("539")
    assert results[0].per100_protein_g == Decimal("6.3")
    assert results[0].barcode == "3017620422003"


def test_search_falls_back_to_legacy_when_modern_unreachable(monkeypatch):
    calls: list[str] = []

    def fake_get(url, params=None, timeout=None, headers=None):
        calls.append(url)
        if "search.openfoodfacts.org" in url:
            raise httpx.ConnectError("modern search down")
        return _Resp({"products": [_HIT]})

    monkeypatch.setattr(off.httpx, "get", fake_get)
    results = OpenFoodFactsClient().search("nutella")

    assert any("search.openfoodfacts.org" in u for u in calls)
    assert any("/cgi/search.pl" in u for u in calls)
    assert len(results) == 1
    assert results[0].name == "Nutella"
