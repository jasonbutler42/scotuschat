"""Add is_justice boolean column to the people table.

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-29

Adds a NOT NULL BOOLEAN column `is_justice` to the `people` table with a
server default of FALSE. Backfills `is_justice = TRUE` for every person who
has at least one row in `court_tenures` (i.e., has served on the bench).
All other people retain the default FALSE.

Column type: BOOLEAN NOT NULL DEFAULT FALSE

Backfill source: court_tenures only (D-01, D-02). No side-based inference
is performed — if a person has no tenure rows they default FALSE regardless
of how they appeared in arguments.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the column as NOT NULL with server_default FALSE.
    # PostgreSQL fills existing rows with FALSE via the server default,
    # so no separate UPDATE for the FALSE case is needed.
    op.add_column(
        "people",
        sa.Column("is_justice", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    # Backfill: set is_justice = TRUE for every person with court_tenures rows.
    # D-02: backfill source is court_tenures ONLY — no side-based inference.
    op.execute(
        """
        UPDATE people
        SET is_justice = TRUE
        WHERE id IN (SELECT DISTINCT person_id FROM court_tenures)
        """
    )


def downgrade() -> None:
    op.drop_column("people", "is_justice")
