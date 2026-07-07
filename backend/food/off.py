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

# OFF asks for a descriptive User-Agent with contact info and rate-limits / blocks generic
# ones; include an app URL + contact so search/barcode requests aren't throttled.
_USER_AGENT = "fitness-tracker/0.1 (https://fitness-tracker.kipphard.com; akipphard@yahoo.de)"


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
    # Modern full-text search service (Search-a-licious). The legacy /cgi/search.pl endpoint
    # on BASE is deprecated and frequently returns 5xx, so it is only a best-effort fallback.
    SEARCH_BASE = "https://search.openfoodfacts.org"
    _FIELDS = "code,product_name,nutriments,serving_quantity"

    def __init__(self, lc: str = "de", timeout: float = 8.0) -> None:
        self._lc = lc
        self._timeout = timeout

    def _request(self, url: str, params: dict, timeout: float | None = None) -> dict:
        resp = httpx.get(
            url,
            params=params,
            timeout=timeout or self._timeout,
            headers={"User-Agent": _USER_AGENT},
        )
        resp.raise_for_status()
        return resp.json()

    def _get(self, path: str, params: dict) -> dict:
        return self._request(f"{self.BASE}{path}", params)

    def get_product(self, barcode: str) -> FoodData | None:
        data = self._get(
            f"/api/v2/product/{barcode}.json",
            {"lc": self._lc, "fields": self._FIELDS},
        )
        if data.get("status") != 1:
            return None
        return parse_product(data.get("product") or {}, barcode)

    def search(self, query: str, limit: int = 10) -> list[FoodData]:
        """Full-text product search via the modern Search-a-licious service.

        Falls back to the deprecated /cgi/search.pl endpoint only if the modern service is
        unreachable; if both fail the exception propagates so the route reports 502.
        """
        try:
            return self._search_modern(query, limit)
        except Exception:  # noqa: BLE001 - modern search unreachable; try the legacy endpoint
            return self._search_legacy(query, limit)

    def _search_modern(self, query: str, limit: int) -> list[FoodData]:
        data = self._request(
            f"{self.SEARCH_BASE}/search",
            {
                "q": query,
                "page_size": limit,
                "lang": self._lc,
                "fields": self._FIELDS,
            },
            timeout=max(self._timeout, 10.0),
        )
        return self._parse_hits(data.get("hits"))

    def _search_legacy(self, query: str, limit: int) -> list[FoodData]:
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
        return self._parse_hits(data.get("products"))

    @staticmethod
    def _parse_hits(products: list[dict] | None) -> list[FoodData]:
        out: list[FoodData] = []
        for product in products or []:
            parsed = parse_product(product, product.get("code"))
            if parsed is not None:
                out.append(parsed)
        return out
