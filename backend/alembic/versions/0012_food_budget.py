"""food budget — issue #5 §4

Adds a weekly food budget + currency to settings, and an estimated per-line price to shopping
items. All nullable — existing rows keep working; the UI defaults the currency to EUR.

Revision ID: 0012
Revises: 0011
Create Date: 2026-06-23
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "settings", sa.Column("food_budget_weekly", sa.Numeric(10, 2), nullable=True)
    )
    op.add_column("settings", sa.Column("currency", sa.String(3), nullable=True))
    op.add_column(
        "shopping_items", sa.Column("price", sa.Numeric(10, 2), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("shopping_items", "price")
    op.drop_column("settings", "currency")
    op.drop_column("settings", "food_budget_weekly")
