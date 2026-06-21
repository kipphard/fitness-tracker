"""step_logs + settings.eat_back_activity — Phase 6 (steps)

Adds the per-user daily step log and the "eat back activity calories" preference. Explicit
migration; no metadata.create_all. The settings column gets a server_default so existing rows
backfill to false.

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from backend.persistence.types import GUID

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "settings",
        sa.Column(
            "eat_back_activity",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    op.create_table(
        "step_logs",
        sa.Column("id", GUID, primary_key=True),
        sa.Column(
            "user_id",
            GUID,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("steps", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "date", name="uq_step_logs_user_date"),
    )
    op.create_index("ix_step_logs_user_id", "step_logs", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_step_logs_user_id", table_name="step_logs")
    op.drop_table("step_logs")
    op.drop_column("settings", "eat_back_activity")
