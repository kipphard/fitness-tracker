"""initial schema: users, profiles, settings — Phase 0

Explicit, frozen baseline: creates the Phase 0 tables only. Later phases add columns/tables
in their own revisions. Do NOT use metadata.create_all here — the metadata is not frozen and
would drift as the models evolve; this baseline must keep describing exactly the Phase 0 schema.

Revision ID: 0001
Revises:
Create Date: 2026-06-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from backend.calories.engine import ActivityLevel, Gender, Goal
from backend.persistence.models import Language, UnitSystem
from backend.persistence.types import GUID, Measure

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", GUID, primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "profiles",
        sa.Column("id", GUID, primary_key=True),
        sa.Column(
            "user_id",
            GUID,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("height_cm", Measure, nullable=False),
        sa.Column("age", sa.Integer, nullable=False),
        sa.Column("gender", sa.Enum(Gender, name="gender"), nullable=False),
        sa.Column("weight_kg", Measure, nullable=False),
        sa.Column(
            "activity_level",
            sa.Enum(ActivityLevel, name="activity_level"),
            nullable=False,
        ),
        sa.Column("goal", sa.Enum(Goal, name="goal"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "settings",
        sa.Column("id", GUID, primary_key=True),
        sa.Column(
            "user_id",
            GUID,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("language", sa.Enum(Language, name="language"), nullable=False),
        sa.Column(
            "unit_system", sa.Enum(UnitSystem, name="unit_system"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("settings")
    op.drop_table("profiles")
    op.drop_table("users")
    # Drop the Postgres ENUM types the tables created (no-op on SQLite).
    bind = op.get_bind()
    for name in ("unit_system", "language", "goal", "activity_level", "gender"):
        sa.Enum(name=name).drop(bind, checkfirst=True)
