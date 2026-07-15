"""Rename court_tenures.seat to office without changing legacy values.

Revision ID: 0020
Revises: 0019
Create Date: 2026-07-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0020"
down_revision: str = "0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "court_tenures",
        "seat",
        new_column_name="office",
        existing_type=sa.String(length=100),
        existing_nullable=True,
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "court_tenures",
        "office",
        new_column_name="seat",
        existing_type=sa.String(length=100),
        existing_nullable=True,
        nullable=True,
    )
