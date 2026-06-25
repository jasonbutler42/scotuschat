"""Expand side enum and add argument_status column.

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-25

This migration performs two schema changes required by Phase 15:

Part 1 — Expand the `side` PG enum type with three new values:
  PETITIONER, RESPONDENT, AMICUS
  ADVOCATE stays permanently (PG cannot drop enum values) and is treated as
  legacy. UNKNOWN means "advocate, role not yet determined."
  All existing argument_participants rows where side='ADVOCATE' are backfilled
  to side='UNKNOWN' (D-06).

Part 2 — Add the `arguments.status` enum column:
  New PG enum type `argument_status` with values ('pipeline', 'draft', 'published').
  Existing rows are backfilled by precedence:
    published_at IS NOT NULL  → 'published'
    resolved_at  IS NOT NULL AND published_at IS NULL → 'draft'
    resolved_at  IS NULL      → 'pipeline'
  The column is then made NOT NULL.

Deployment order constraint:
  Run `alembic upgrade head` BEFORE deploying API code that references the new
  SideEnum members (PETITIONER, RESPONDENT, AMICUS). If code is deployed before
  the migration runs, SQLAlchemy will attempt to write enum values that the PG
  type does not yet contain (15-RESEARCH Pitfall 3).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Part A: Expand the `side` PG enum type with three new values.
    #
    # CRITICAL: ALTER TYPE ... ADD VALUE cannot run inside a transaction
    # block. Commit Alembic's implicit open transaction before the ADD VALUE
    # calls (15-RESEARCH Pitfall 1). Transactional DDL/DML resumes after.
    # ------------------------------------------------------------------
    op.execute(sa.text("COMMIT"))
    op.execute(sa.text("ALTER TYPE side ADD VALUE IF NOT EXISTS 'PETITIONER'"))
    op.execute(sa.text("ALTER TYPE side ADD VALUE IF NOT EXISTS 'RESPONDENT'"))
    op.execute(sa.text("ALTER TYPE side ADD VALUE IF NOT EXISTS 'AMICUS'"))

    # ------------------------------------------------------------------
    # Part B: Backfill legacy ADVOCATE rows to UNKNOWN (D-06).
    # After the explicit COMMIT above we are in autocommit mode; subsequent
    # op.execute() calls each run in their own implicit transaction.
    # ------------------------------------------------------------------
    op.execute(sa.text(
        "UPDATE argument_participants SET side = 'UNKNOWN' WHERE side = 'ADVOCATE'"
    ))

    # ------------------------------------------------------------------
    # Part C: Create the `argument_status` PG enum type.
    # Use the DO-block guarded pattern (same as 0001_initial_schema.py) to
    # make the migration idempotent.
    # ------------------------------------------------------------------
    op.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE argument_status AS ENUM ('pipeline', 'draft', 'published');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """))

    # ------------------------------------------------------------------
    # Part D: Add the `arguments.status` column (nullable initially for
    # the backfill that follows).
    # ------------------------------------------------------------------
    op.add_column(
        "arguments",
        sa.Column(
            "status",
            sa.Enum("pipeline", "draft", "published", name="argument_status"),
            nullable=True,
        ),
    )

    # ------------------------------------------------------------------
    # Part E: Backfill status from existing lifecycle columns — three
    # UPDATE statements in precedence order so every row receives a value.
    # ------------------------------------------------------------------
    op.execute(sa.text(
        "UPDATE arguments SET status = 'published' WHERE published_at IS NOT NULL"
    ))
    op.execute(sa.text(
        "UPDATE arguments SET status = 'draft' "
        "WHERE resolved_at IS NOT NULL AND published_at IS NULL"
    ))
    op.execute(sa.text(
        "UPDATE arguments SET status = 'pipeline' WHERE resolved_at IS NULL"
    ))

    # ------------------------------------------------------------------
    # Part F: Enforce NOT NULL now that every row has been backfilled.
    # ------------------------------------------------------------------
    op.alter_column("arguments", "status", nullable=False)


def downgrade() -> None:
    # Remove the status column and its enum type.
    op.drop_column("arguments", "status")
    op.execute(sa.text("DROP TYPE IF EXISTS argument_status"))

    # NOTE: The PETITIONER, RESPONDENT, and AMICUS values added to the
    # `side` enum type are NOT reversed here. PostgreSQL does not support
    # removing enum values — they remain in the type permanently. The
    # downgrade also does not restore ADVOCATE rows from UNKNOWN because
    # ADVOCATE and UNKNOWN are semantically equivalent legacy values and
    # restoring them would require per-row identity that was not captured.
