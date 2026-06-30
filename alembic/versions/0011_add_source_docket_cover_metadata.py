"""Add source_docket and cover_metadata JSONB to arguments; make argued_date nullable.

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-30

Adds two new nullable columns to the `arguments` table and alters
`argued_date` to allow NULL values:

- `source_docket VARCHAR(50) NULL` — tracks the primary docket used at ingest
  time for deduplication (D-01). NULL when operator did not supply a docket at
  pipeline start.
- `cover_metadata JSONB NULL` — stores the raw output of the cover extractor
  after each parse step (D-07). Always written by parse; read by the job detail
  page to render hint text.
- `argued_date DATE` — changed from NOT NULL to NULL (D-08). Job-driven ingest
  leaves it NULL instead of inserting a synthetic `date.today()` placeholder.
  Existing rows retain their values; no backfill needed.

Unique constraint `uq_arguments_source_docket_question` on
(source_docket, question_number) prevents duplicate argument rows when a
docket is known. PostgreSQL NULL semantics apply — multiple rows with
source_docket = NULL and the same question_number do NOT violate this
constraint (NULL != NULL in unique index evaluation per SQL standard). This
is expected and documented in D-01.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add source_docket — nullable, no server default.
    # Tracks the primary docket number supplied at ingest time (D-01).
    op.add_column(
        "arguments",
        sa.Column("source_docket", sa.String(50), nullable=True),
    )

    # Add cover_metadata JSONB — nullable, no server default.
    # Always written by parse step after cover extraction (D-07).
    op.add_column(
        "arguments",
        sa.Column("cover_metadata", postgresql.JSONB(), nullable=True),
    )

    # Make argued_date nullable (was NOT NULL).
    # Existing rows all have argued_date set — no backfill required.
    # Job-driven ingest will leave it NULL going forward (D-08).
    op.alter_column("arguments", "argued_date", nullable=True)

    # UNIQUE constraint on (source_docket, question_number).
    # NULL semantics: multiple rows with source_docket = NULL do NOT violate
    # this constraint — deduplication only applies when docket is known (D-01).
    op.create_unique_constraint(
        "uq_arguments_source_docket_question",
        "arguments",
        ["source_docket", "question_number"],
    )


def downgrade() -> None:
    # Reverse order of upgrade operations.
    op.drop_constraint("uq_arguments_source_docket_question", "arguments", type_="unique")
    op.alter_column("arguments", "argued_date", nullable=False)
    op.drop_column("arguments", "cover_metadata")
    op.drop_column("arguments", "source_docket")
