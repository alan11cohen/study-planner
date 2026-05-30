"""initial_schema

Revision ID: 0001
Revises:
Create Date: 2026-04-29

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)

    op.create_table(
        "study_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("goal", sa.String(), nullable=False),
        sa.Column("hours_per_week", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_study_plans_id"), "study_plans", ["id"], unique=False)

    op.create_table(
        "study_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("estimated_hours", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["study_plans.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_study_tasks_id"), "study_tasks", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_study_tasks_id"), table_name="study_tasks")
    op.drop_table("study_tasks")
    op.drop_index(op.f("ix_study_plans_id"), table_name="study_plans")
    op.drop_table("study_plans")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")
