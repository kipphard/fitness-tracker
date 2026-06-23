"""settings: food-planning preferences — issue #5 §2

Adds ``country``, ``store`` and ``dietary_preferences`` to the settings table so the AI
day-plan / meal generator can be constrained to realistic products for the user's country +
store (set once, reused per run). All nullable — existing rows keep working.

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-23
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("settings", sa.Column("country", sa.String(80), nullable=True))
    op.add_column("settings", sa.Column("store", sa.String(120), nullable=True))
    op.add_column(
        "settings", sa.Column("dietary_preferences", sa.String(500), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("settings", "dietary_preferences")
    op.drop_column("settings", "store")
    op.drop_column("settings", "country")
