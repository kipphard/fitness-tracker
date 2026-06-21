"""Open Food Facts client (Phase 4).

A thin wrapper over the public OFF API (no key required): barcode lookup and text search,
returning normalized per-100g nutrition. German product names via ``lc=de``. OFF is
community data and rate-limited (~15 req/min/IP), so callers should cache results locally.

The client is injected via a FastAPI dependency so tests can substitute a fake (see
``backend.api.deps.get_off_client``). It is kept behind the ``FoodData`` shape so a
self-hosted OFF dump could replace it later without touching callers.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

_USER_AGENT = "fitness-tracker/0.1 (self-hosted)"


@dataclass(frozen=True)
class FoodData:
    name: str
    barcode: str | None
    per100_kcal: Decimal
    per100_protein_g: Decimal
    per100_fat_g: Decimal
    per100_carbs_g: Decimal
    serving_g: Decimal | None


def _dec(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def parse_product(product: dict, barcode: str | None) -> FoodData | None:
    """Normalize an OFF product dict, or None if it lacks usable energy data."""
    nutriments = product.get("nutriments") or {}
    kcal = _dec(nutriments.get("energy-kcal_100g"))
    if kcal is None:
        return None  # no per-100g energy → not loggable
    name = (product.get("product_name") or "").strip() or (barcode or "Unknown")
    code = product.get("code") or barcode
    return FoodData(
        name=name[:200],
        barcode=str(code) if code else None,
        per100_kcal=kcal,
        per100_protein_g=_dec(nutriments.get("proteins_100g")) or Decimal(0),
        per100_fat_g=_dec(nutriments.get("fat_100g")) or Decimal(0),
        per100_carbs_g=_dec(nutriments.get("carbohydrates_100g")) or Decimal(0),
        serving_g=_dec(product.get("serving_quantity")),
    )


class OpenFoodFactsClient:
    BASE = "https://world.openfoodfacts.org"
    _FIELDS = "code,product_name,nutriments,serving_quantity"

    def __init__(self, lc: str = "de", timeout: float = 8.0) -> None:
        self._lc = lc
        self._timeout = timeout

    def _get(self, path: str, params: dict) -> dict:
        resp = httpx.get(
            f"{self.BASE}{path}",
            params=params,
            timeout=self._timeout,
            headers={"User-Agent": _USER_AGENT},
        )
        resp.raise_for_status()
        return resp.json()

    def get_product(self, barcode: str) -> FoodData | None:
        data = self._get(
            f"/api/v2/product/{barcode}.json",
            {"lc": self._lc, "fields": self._FIELDS},
        )
        if data.get("status") != 1:
            return None
        return parse_product(data.get("product") or {}, barcode)

    def search(self, query: str, limit: int = 10) -> list[FoodData]:
        data = self._get(
            "/cgi/search.pl",
            {
                "search_terms": query,
                "search_simple": 1,
                "action": "process",
                "json": 1,
                "page_size": limit,
                "lc": self._lc,
                "fields": self._FIELDS,
            },
        )
        out: list[FoodData] = []
        for product in data.get("products") or []:
            parsed = parse_product(product, product.get("code"))
            if parsed is not None:
                out.append(parsed)
        return out
