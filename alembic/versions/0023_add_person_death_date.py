"""Add people.death_date DATE NULL — Bench editor Death Date field (Phase 39 D-04).

Revision ID: 0023
Revises: 0022
Create Date: 2026-07-28

Adds people.death_date DATE NULL. Migration 0016 ("Add people.birthdate")
explicitly deferred this column ("Person 'Death Date' — UI renders a
disabled placeholder input with no backing column; deferred to a future
phase") — this migration is that future phase's fulfillment.

No backfill in this migration — the CSV historical backfill (Plan 39-02's
extension of pipeline/commands/import_justices_csv.py) is an offline
operator-run importer job, not DDL. This migration is a pure column add;
every existing row starts NULL.

Downgrade: drops death_date only.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0023"
down_revision: Union[str, None] = "0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "people",
        sa.Column(
            "death_date",
            sa.Date(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("people", "death_date")
