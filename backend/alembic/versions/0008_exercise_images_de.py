"""exercise images + German names — Phase 7.5

Adds ``name_de`` (best-effort German display name) and ``image_url`` (relative
free-exercise-db image path) to the exercises table, for the expanded library.

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("exercises", sa.Column("name_de", sa.String(200), nullable=True))
    op.add_column("exercises", sa.Column("image_url", sa.String(300), nullable=True))


def downgrade() -> None:
    op.drop_column("exercises", "image_url")
    op.drop_column("exercises", "name_de")
