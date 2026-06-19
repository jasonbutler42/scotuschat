"""Add structured name fields and appointment fields to people table.

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-19

Adds six nullable columns to the people table to support the Phase 9 People
Data Model Migration. All columns default to NULL — no backfill (D-03).

  - first_name VARCHAR(150): structured first name
  - last_name VARCHAR(150): structured last name; used for directory sort (D-07)
  - middle_name VARCHAR(150): structured middle name
  - name_suffix VARCHAR(50): name suffix (Jr., Sr., II, etc.)
  - appointing_president VARCHAR(200): free-text name of appointing president (D-08)
  - appointing_president_party VARCHAR(50): appointing president's party affiliation (D-09)

full_name remains NOT NULL and is not modified by this migration (D-02).
Existing rows are unaffected — all six new columns will be NULL until the
operator fills them in via the admin People Editor.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("people", sa.Column("first_name", sa.String(150), nullable=True))
    op.add_column("people", sa.Column("last_name", sa.String(150), nullable=True))
    op.add_column("people", sa.Column("middle_name", sa.String(150), nullable=True))
    op.add_column("people", sa.Column("name_suffix", sa.String(50), nullable=True))
    op.add_column("people", sa.Column("appointing_president", sa.String(200), nullable=True))
    op.add_column("people", sa.Column("appointing_president_party", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("people", "appointing_president_party")
    op.drop_column("people", "appointing_president")
    op.drop_column("people", "name_suffix")
    op.drop_column("people", "middle_name")
    op.drop_column("people", "last_name")
    op.drop_column("people", "first_name")
