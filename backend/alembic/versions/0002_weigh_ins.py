"""weigh_ins table — Phase 2 (weight tracking)

Adds the per-user daily weigh-in log (one row per user+date). Explicit migration; no
metadata.create_all.

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from backend.persistence.types import GUID, Measure

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "weigh_ins",
        sa.Column("id", GUID, primary_key=True),
        sa.Column(
            "user_id",
            GUID,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("weight_kg", Measure, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "date", name="uq_weigh_ins_user_date"),
    )
    op.create_index("ix_weigh_ins_user_id", "weigh_ins", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_weigh_ins_user_id", table_name="weigh_ins")
    op.drop_table("weigh_ins")
