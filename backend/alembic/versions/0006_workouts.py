"""workouts: exercises, routines, sessions, sets — Phase 7

Explicit migration; no metadata.create_all.

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from backend.persistence.models import ExerciseSource, SetType
from backend.persistence.types import GUID, JSONType, Measure

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "exercises",
        sa.Column("id", GUID, primary_key=True),
        sa.Column(
            "owner_id", GUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True
        ),
        sa.Column(
            "source", sa.Enum(ExerciseSource, name="exercise_source"), nullable=False
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("primary_muscles", JSONType, nullable=True),
        sa.Column("secondary_muscles", JSONType, nullable=True),
        sa.Column("equipment", sa.String(100), nullable=True),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("instructions", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_exercises_owner_id", "exercises", ["owner_id"])

    op.create_table(
        "routines",
        sa.Column("id", GUID, primary_key=True),
        sa.Column(
            "user_id", GUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_routines_user_id", "routines", ["user_id"])

    op.create_table(
        "routine_exercises",
        sa.Column("id", GUID, primary_key=True),
        sa.Column(
            "routine_id",
            GUID,
            sa.ForeignKey("routines.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "exercise_id",
            GUID,
            sa.ForeignKey("exercises.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column("planned_sets", sa.Integer, nullable=False),
        sa.Column("planned_reps", sa.Integer, nullable=True),
    )
    op.create_index(
        "ix_routine_exercises_routine_id", "routine_exercises", ["routine_id"]
    )

    op.create_table(
        "workout_sessions",
        sa.Column("id", GUID, primary_key=True),
        sa.Column(
            "user_id", GUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "routine_id",
            GUID,
            sa.ForeignKey("routines.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("routine_name", sa.String(200), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_workout_sessions_user_id", "workout_sessions", ["user_id"]
    )

    op.create_table(
        "set_logs",
        sa.Column("id", GUID, primary_key=True),
        sa.Column(
            "session_id",
            GUID,
            sa.ForeignKey("workout_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "exercise_id",
            GUID,
            sa.ForeignKey("exercises.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("exercise_name", sa.String(200), nullable=False),
        sa.Column("set_index", sa.Integer, nullable=False),
        sa.Column("weight", Measure, nullable=False),
        sa.Column("reps", sa.Integer, nullable=False),
        sa.Column("set_type", sa.Enum(SetType, name="set_type"), nullable=False),
        sa.Column("rpe", sa.Numeric(3, 1), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_set_logs_session_id", "set_logs", ["session_id"])
    op.create_index("ix_set_logs_exercise_id", "set_logs", ["exercise_id"])


def downgrade() -> None:
    op.drop_index("ix_set_logs_exercise_id", table_name="set_logs")
    op.drop_index("ix_set_logs_session_id", table_name="set_logs")
    op.drop_table("set_logs")
    op.drop_index("ix_workout_sessions_user_id", table_name="workout_sessions")
    op.drop_table("workout_sessions")
    op.drop_index("ix_routine_exercises_routine_id", table_name="routine_exercises")
    op.drop_table("routine_exercises")
    op.drop_index("ix_routines_user_id", table_name="routines")
    op.drop_table("routines")
    op.drop_index("ix_exercises_owner_id", table_name="exercises")
    op.drop_table("exercises")
    bind = op.get_bind()
    for name in ("set_type", "exercise_source"):
        sa.Enum(name=name).drop(bind, checkfirst=True)
