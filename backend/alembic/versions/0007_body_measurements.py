"""body_measurements — Phase 8 (body metrics)

One row per user+date with optional circumference measurements (cm). Explicit migration.

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from backend.persistence.types import GUID, Measure

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "body_measurements",
        sa.Column("id", GUID, primary_key=True),
        sa.Column(
            "user_id", GUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("waist_cm", Measure, nullable=True),
        sa.Column("chest_cm", Measure, nullable=True),
        sa.Column("hips_cm", Measure, nullable=True),
        sa.Column("arm_cm", Measure, nullable=True),
        sa.Column("thigh_cm", Measure, nullable=True),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "date", name="uq_body_measurements_user_date"),
    )
    op.create_index(
        "ix_body_measurements_user_id", "body_measurements", ["user_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_body_measurements_user_id", table_name="body_measurements")
    op.drop_table("body_measurements")
