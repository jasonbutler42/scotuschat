"""Add published_at column to arguments table.

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-22

Adds a nullable published_at column to the arguments table to support the
Phase 11 argument metadata editing and publish workflow (D-05).

  - published_at TIMESTAMP WITH TIME ZONE: operator-controlled publish timestamp

published_at IS NULL means the argument is unpublished (hidden from public /cases/).
published_at IS NOT NULL means the argument is published and visible publicly.

resolved_at is NOT modified by this migration — it retains its existing meaning
(pipeline resolve step completion timestamp). Only published_at controls public
visibility after Phase 11 (D-06).

All existing rows will have published_at = NULL after this migration runs. No
backfill is performed — existing published arguments must be published via the
admin interface.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "arguments",
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("arguments", "published_at")
