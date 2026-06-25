"""shoe size in settings — issue #13

Adds an optional EU shoe size to settings, used as a rough stride basis by the km->steps
calculator. Nullable — existing rows keep working.

Revision ID: 0014
Revises: 0013
Create Date: 2026-06-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("settings", sa.Column("shoe_size_eu", sa.Numeric(4, 1), nullable=True))


def downgrade() -> None:
    op.drop_column("settings", "shoe_size_eu")
