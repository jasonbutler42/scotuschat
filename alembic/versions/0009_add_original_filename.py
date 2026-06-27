"""Add original_filename column to admin_jobs table.

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-27

Adds a nullable TEXT column `original_filename` to the `admin_jobs` table.
This stores the browser-supplied filename when a PDF is uploaded via the
admin UI (upload mode). URL-mode jobs receive NULL.

No backfill — existing rows receive NULL. The frontend hides the filename
display when the value is NULL (conditional render).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("admin_jobs", sa.Column("original_filename", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("admin_jobs", "original_filename")
