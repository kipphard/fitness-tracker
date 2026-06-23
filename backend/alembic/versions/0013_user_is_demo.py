"""users.is_demo — public live demo

Adds the ``is_demo`` flag to users. Demo users are ephemeral public-demo sandboxes (seeded on
creation, deleted with all their rows after the TTL, blocked from paid AI endpoints). Existing
users default to false. Per-user data isolation is unchanged.

Revision ID: 0013
Revises: 0012
Create Date: 2026-06-23
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("users", "is_demo")
