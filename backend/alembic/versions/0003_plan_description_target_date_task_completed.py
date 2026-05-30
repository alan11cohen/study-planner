"""plan_description_target_date_task_completed

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-29

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("study_plans", sa.Column("description", sa.String(), nullable=True))
    op.add_column("study_plans", sa.Column("target_date", sa.Date(), nullable=True))
    op.add_column(
        "study_tasks",
        sa.Column("completed", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("study_tasks", "completed")
    op.drop_column("study_plans", "target_date")
    op.drop_column("study_plans", "description")
