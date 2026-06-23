"""shopping list — issue #5 §3

A per-user shopping list generated from a day plan minus the pantry (or added manually).
One row per item (unique lowercased name key); food_id links back to a saved food when known.

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-23
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from backend.persistence.types import GUID, Measure

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "shopping_items",
        sa.Column("id", GUID, nullable=False),
        sa.Column("user_id", GUID, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("name_key", sa.String(200), nullable=False),
        sa.Column("food_id", GUID, nullable=True),
        sa.Column("amount_g", Measure, nullable=True),
        sa.Column("checked", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["food_id"], ["foods.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name_key", name="uq_shopping_user_name"),
    )
    op.create_index(
        "ix_shopping_items_user_id", "shopping_items", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_shopping_items_user_id", table_name="shopping_items")
    op.drop_table("shopping_items")
