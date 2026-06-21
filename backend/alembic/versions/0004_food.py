"""foods + food_logs — Phase 4 (food tracking)

Adds the per-user food catalogue (custom + Open Food Facts cache) and the diary log.
Explicit migration; no metadata.create_all.

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from backend.persistence.models import FoodSource, MealSlot
from backend.persistence.types import GUID, Macro, Measure

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "foods",
        sa.Column("id", GUID, primary_key=True),
        sa.Column(
            "owner_id",
            GUID,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source", sa.Enum(FoodSource, name="food_source"), nullable=False),
        sa.Column("barcode", sa.String(50), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("per100_kcal", Measure, nullable=False),
        sa.Column("per100_protein_g", Measure, nullable=False),
        sa.Column("per100_fat_g", Measure, nullable=False),
        sa.Column("per100_carbs_g", Measure, nullable=False),
        sa.Column("serving_g", Measure, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("owner_id", "barcode", name="uq_foods_owner_barcode"),
    )
    op.create_index("ix_foods_owner_id", "foods", ["owner_id"])

    op.create_table(
        "food_logs",
        sa.Column("id", GUID, primary_key=True),
        sa.Column(
            "user_id",
            GUID,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("slot", sa.Enum(MealSlot, name="meal_slot"), nullable=False),
        sa.Column(
            "food_id", GUID, sa.ForeignKey("foods.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("food_name", sa.String(200), nullable=False),
        sa.Column("amount_g", Measure, nullable=False),
        sa.Column("kcal", Macro, nullable=False),
        sa.Column("protein_g", Macro, nullable=False),
        sa.Column("fat_g", Macro, nullable=False),
        sa.Column("carbs_g", Macro, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_food_logs_user_id", "food_logs", ["user_id"])
    op.create_index("ix_food_logs_user_date", "food_logs", ["user_id", "date"])


def downgrade() -> None:
    op.drop_index("ix_food_logs_user_date", table_name="food_logs")
    op.drop_index("ix_food_logs_user_id", table_name="food_logs")
    op.drop_table("food_logs")
    op.drop_index("ix_foods_owner_id", table_name="foods")
    op.drop_table("foods")
    bind = op.get_bind()
    for name in ("meal_slot", "food_source"):
        sa.Enum(name=name).drop(bind, checkfirst=True)
