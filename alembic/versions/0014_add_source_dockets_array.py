"""Add arguments.source_dockets text[] — full ordered docket list for consolidated cases.

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-06

Adds arguments.source_dockets ARRAY(VARCHAR(50)) NULL — stores the complete ordered list
of docket numbers for an argument, enabling consolidated cases to record multiple dockets.

Design decision D-MULTI-DOCKET:
  source_docket (String(50)) is RETAINED unchanged. It participates in the UNIQUE constraint
  uq_arguments_source_docket_question (source_docket, question_number) used by ingest,
  parse, and the duplicate-check preflight. source_docket remains dockets[0] — the
  canonical dedup key — and is kept in sync by the service layer whenever source_dockets
  is written.

Backfill: for every existing row where source_docket IS NOT NULL, source_dockets is set
to ARRAY[source_docket]. Rows with NULL source_docket keep NULL source_dockets (the
NULL-when-cleared semantics mirror the source_docket column).

Downgrade: drops source_dockets only. source_docket and the unique constraint are untouched.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add arguments.source_dockets — nullable text[] for the full ordered docket list.
    op.add_column(
        "arguments",
        sa.Column(
            "source_dockets",
            postgresql.ARRAY(sa.String(50)),
            nullable=True,
        ),
    )

    # 2. Backfill: for rows with a known source_docket, initialise source_dockets
    #    to a single-element array. NULL rows remain NULL (D-MULTI-DOCKET NULL semantics).
    op.execute(
        "UPDATE arguments SET source_dockets = ARRAY[source_docket] WHERE source_docket IS NOT NULL"
    )


def downgrade() -> None:
    # Drop source_dockets only. source_docket and the unique constraint predate this
    # migration and are left intact.
    op.drop_column("arguments", "source_dockets")
