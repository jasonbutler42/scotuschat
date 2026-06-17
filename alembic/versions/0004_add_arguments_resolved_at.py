"""Add resolved_at column to arguments table.

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-17

Adds arguments.resolved_at (TIMESTAMPTZ nullable):
  - NULL = resolve step has not completed → argument is hidden from /cases/
  - Non-NULL = resolve completed; argument is visible in the public case list
  - Set by resolve completion paths (api/services/admin_jobs.py resolve_job
    and pipeline/commands/resolve.py all-auto-resolved fallback)
  - No backfill: existing argument rows stay NULL (hidden) until re-resolved.
    This is the intended behavior — placeholder ingest rows should not be
    visible until a real resolve completes.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "arguments",
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("arguments", "resolved_at")
