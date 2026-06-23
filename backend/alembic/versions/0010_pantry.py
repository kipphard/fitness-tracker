"""pantry items — issue #5 §2

A per-user list of foods the user has at home; suggestions + day plans prefer these.
References a saved food (cascade-deleted with it). Unique per (user, food).

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-23
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from backend.persistence.types import GUID

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pantry_items",
        sa.Column("id", GUID, nullable=False),
        sa.Column("user_id", GUID, nullable=False),
        sa.Column("food_id", GUID, nullable=False),
        sa.Column("note", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["food_id"], ["foods.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "food_id", name="uq_pantry_user_food"),
    )
    op.create_index(
        "ix_pantry_items_user_id", "pantry_items", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_pantry_items_user_id", table_name="pantry_items")
    op.drop_table("pantry_items")
