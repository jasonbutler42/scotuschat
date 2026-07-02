"""Add argument_participants.title; move appointed_by to court_tenures; drop people.appointing_president columns.

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-02

Adds argument_participants.title VARCHAR(500) NULL — stores the advocate's subtitle
line from the TOC (e.g. "Solicitor General") populated by the parse step (PJOB-13).

Moves appointment-tracking columns from the people table to court_tenures:
  - court_tenures.appointed_by VARCHAR(200) NULL (formerly people.appointing_president)
  - court_tenures.appointing_president_party VARCHAR(50) NULL

Drops people.appointing_president and people.appointing_president_party. Existing
data in those columns is known test/incorrect data — no backfill (D-08). The Phase 27
UI allows operators to fill the correct per-tenure values.

No backfill on any of the three new columns. All NULL values are expected at migration time.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add argument_participants.title — nullable, schema half of PJOB-13.
    op.add_column(
        "argument_participants",
        sa.Column("title", sa.String(500), nullable=True),
    )

    # 2. Add court_tenures.appointed_by — nullable; replaces people.appointing_president.
    #    Column is named appointed_by per the resolved user decision (D-08/A4).
    op.add_column(
        "court_tenures",
        sa.Column("appointed_by", sa.String(200), nullable=True),
    )

    # 3. Add court_tenures.appointing_president_party — nullable; mirrors the old people column.
    op.add_column(
        "court_tenures",
        sa.Column("appointing_president_party", sa.String(50), nullable=True),
    )

    # 4. Drop people.appointing_president — data is test/incorrect (D-08); no backfill.
    op.drop_column("people", "appointing_president")

    # 5. Drop people.appointing_president_party — same rationale as above.
    op.drop_column("people", "appointing_president_party")


def downgrade() -> None:
    # Reverse in opposite order of upgrade.

    # Restore people.appointing_president_party as nullable.
    op.add_column(
        "people",
        sa.Column("appointing_president_party", sa.String(50), nullable=True),
    )

    # Restore people.appointing_president as nullable.
    op.add_column(
        "people",
        sa.Column("appointing_president", sa.String(200), nullable=True),
    )

    # Drop court_tenures.appointing_president_party.
    op.drop_column("court_tenures", "appointing_president_party")

    # Drop court_tenures.appointed_by.
    op.drop_column("court_tenures", "appointed_by")

    # Drop argument_participants.title.
    op.drop_column("argument_participants", "title")
