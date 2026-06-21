"""macro_targets table — Phase 3 (macros)

Adds the per-user macro preferences (protein/fat grams per kg of bodyweight). Explicit
migration; no metadata.create_all.

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from backend.persistence.types import GUID, Measure

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "macro_targets",
        sa.Column("id", GUID, primary_key=True),
        sa.Column(
            "user_id",
            GUID,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("protein_g_per_kg", Measure, nullable=False),
        sa.Column("fat_g_per_kg", Measure, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("macro_targets")
