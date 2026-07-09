"""Add people.birthdate DATE NULL — Bench editor Birth Date field (PEDIT-02).

Revision ID: 0016
Revises: 0015
Create Date: 2026-07-09

Adds people.birthdate DATE NULL. There is no source data for birthdate
anywhere in the pipeline or prior schema, so no backfill is performed —
all existing people rows are expected to remain NULL after this migration
until an operator fills them in via the People editor.

Explicitly NOT added this phase (deferred per D-12/D-14, Phase 27):
  - Person "Death Date" — UI renders a disabled placeholder input with no
    backing column; deferred to a future phase.
  - CourtTenure "reason left the bench" — UI renders a disabled placeholder
    input with no backing column; deferred to a future phase.

Downgrade: drops birthdate only.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0016"
down_revision: Union[str, None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "people",
        sa.Column(
            "birthdate",
            sa.Date(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("people", "birthdate")
