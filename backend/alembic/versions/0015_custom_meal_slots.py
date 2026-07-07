"""user-defined meal slots

Moves ``food_logs.slot`` off the closed ``meal_slot`` Postgres enum to free text so users can
log to their own custom slots, and adds ``settings.meal_slots`` (the per-user ordered slot list).
Existing slot values are preserved as text.

Revision ID: 0015
Revises: 0014
Create Date: 2026-07-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from backend.persistence.types import JSONType

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_MEAL_SLOT_ENUM = sa.Enum("breakfast", "lunch", "dinner", "snack", name="meal_slot")


def upgrade() -> None:
    op.add_column("settings", sa.Column("meal_slots", JSONType, nullable=True))

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.alter_column(
            "food_logs",
            "slot",
            existing_type=_MEAL_SLOT_ENUM,
            type_=sa.String(length=50),
            existing_nullable=False,
            postgresql_using="slot::text",
        )
        _MEAL_SLOT_ENUM.drop(bind, checkfirst=True)
    else:
        # SQLite can't ALTER COLUMN TYPE in place — batch mode recreates the table (and drops
        # the enum's CHECK constraint). Prod is Postgres; this keeps the chain runnable anywhere.
        with op.batch_alter_table("food_logs") as batch:
            batch.alter_column("slot", type_=sa.String(length=50), existing_nullable=False)


def downgrade() -> None:
    op.drop_column("settings", "meal_slots")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # Custom slots can't be represented by the enum — fold them into 'snack' first.
        op.execute(
            "UPDATE food_logs SET slot = 'snack' "
            "WHERE slot NOT IN ('breakfast', 'lunch', 'dinner', 'snack')"
        )
        _MEAL_SLOT_ENUM.create(bind, checkfirst=True)
        op.alter_column(
            "food_logs",
            "slot",
            existing_type=sa.String(length=50),
            type_=_MEAL_SLOT_ENUM,
            existing_nullable=False,
            postgresql_using="slot::meal_slot",
        )
    else:
        with op.batch_alter_table("food_logs") as batch:
            batch.alter_column("slot", type_=sa.String(length=50), existing_nullable=False)
