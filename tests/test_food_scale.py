"""Pure food helpers — portion scaling and Open Food Facts parsing."""
from decimal import Decimal

from backend.food.off import parse_product
from backend.food.scale import scale_per100


def test_scale_per100():
    s = scale_per100(
        per100_kcal=Decimal("200"),
        per100_protein_g=Decimal("10"),
        per100_fat_g=Decimal("5"),
        per100_carbs_g=Decimal("30"),
        amount_g=Decimal("150"),
    )
    assert s.kcal == Decimal("300")  # 200 * 1.5
    assert s.protein_g == Decimal("15")
    assert s.fat_g == Decimal("7.5")
    assert s.carbs_g == Decimal("45")


def test_parse_product_normalizes():
    product = {
        "code": "123",
        "product_name": "Müsli",
        "serving_quantity": "40",
        "nutriments": {
            "energy-kcal_100g": 375,
            "proteins_100g": 10.5,
            "fat_100g": 6,
            "carbohydrates_100g": 70,
        },
    }
    fd = parse_product(product, "123")
    assert fd is not None
    assert fd.name == "Müsli"
    assert fd.barcode == "123"
    assert fd.per100_kcal == Decimal("375")
    assert fd.per100_protein_g == Decimal("10.5")
    assert fd.serving_g == Decimal("40")


def test_parse_product_without_energy_is_none():
    assert parse_product({"product_name": "x", "nutriments": {}}, "1") is None
