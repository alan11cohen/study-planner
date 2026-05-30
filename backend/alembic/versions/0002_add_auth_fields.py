"""add_auth_fields

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-29

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(), nullable=True))
    op.create_unique_constraint("uq_users_name", "users", ["name"])


def downgrade() -> None:
    op.drop_constraint("uq_users_name", "users", type_="unique")
    op.drop_column("users", "password_hash")
