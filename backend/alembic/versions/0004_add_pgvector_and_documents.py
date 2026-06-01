"""add pgvector extension and plan_documents table

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-31

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "plan_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["study_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_plan_documents_id", "plan_documents", ["id"])
    op.create_index("ix_plan_documents_plan_id", "plan_documents", ["plan_id"])


def downgrade() -> None:
    op.drop_index("ix_plan_documents_plan_id", table_name="plan_documents")
    op.drop_index("ix_plan_documents_id", table_name="plan_documents")
    op.drop_table("plan_documents")
