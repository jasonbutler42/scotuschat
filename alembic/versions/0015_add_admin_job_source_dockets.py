"""Add admin_jobs.source_dockets text[] — run-start docket list survives job creation.

Revision ID: 0015
Revises: 0014
Create Date: 2026-07-07

Adds admin_jobs.source_dockets ARRAY(VARCHAR(50)) NULL — stores the full ordered
list of docket pills submitted by the operator when a run is started, before the
Argument row exists.

Design decision (D-07 supersession, Phase 24 Plan 04):
  The original CONTEXT.md decision D-07 called for an immediate PATCH of the new
  argument's source_dockets right after job creation. That is not implementable
  because argument_id is null until the ingest subprocess completes. Instead, the
  full ordered docket list is carried as run-start metadata: SvelteKit forwards
  every submitted pill to FastAPI as repeated source_dockets values, the router
  normalizes/dedupes them, and jobs_service.create_job stores the list here on
  admin_jobs. The router then passes the first docket as --primary-docket and the
  remainder as --dockets to the ingest subprocess, which writes the full ordered
  list to Argument.source_dockets when it creates the Argument row.

Backfill: none. Existing admin_jobs rows keep NULL source_dockets — they predate
this column and their originally submitted dockets (if any) are not recoverable
from admin_jobs itself.

Downgrade: drops source_dockets only.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "admin_jobs",
        sa.Column(
            "source_dockets",
            postgresql.ARRAY(sa.String(50)),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("admin_jobs", "source_dockets")
