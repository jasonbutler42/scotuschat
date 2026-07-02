"""Add unpublished to argument_status enum; create argument_status_log table with backfill.

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-02

This migration performs two schema changes required by Phase 22:

Part 1 — Expand the `argument_status` PG enum with a new value:
  `unpublished` — an operator-set status that hides an argument from the public
  site without deleting it. This differs from `draft` (pipeline-incomplete) by
  being an explicit editorial hold.

  CRITICAL: ALTER TYPE ADD VALUE cannot run inside a transaction block. Alembic's
  implicit transaction is committed first (same discipline as migration 0008 for
  the `side` enum expansion). The enum value is NOT removed on downgrade because
  PostgreSQL does not support removing enum values.

Part 2 — Create the `argument_status_log` table:
  Stores a log of status changes for each argument. Minimal schema (D-06): id,
  argument_id (FK→arguments.id), status, created_at. No previous_status, notes,
  or triggered_by in v1.5.

  The `status` column binds to the existing `argument_status` PG enum type
  (name="argument_status") — it does NOT create a shadow type.

Part 3 — Backfill:
  Seeds one log row per existing argument using each argument's CURRENT status
  value (not a hardcoded literal). Uses COALESCE(resolved_at, CURRENT_TIMESTAMP)
  as the timestamp so the seeded row reflects when the pipeline resolve step
  completed (T-22-02 mitigation).

Downstream: Phases 26 and 27 (argument status lifecycle UI and status timeline)
depend on this enum value and log table.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Part 1: Expand the `argument_status` PG enum with 'unpublished'.
    #
    # CRITICAL: ALTER TYPE ... ADD VALUE cannot run inside a transaction
    # block. Commit Alembic's implicit open transaction before the ADD VALUE
    # call (same discipline as migration 0008 which established this pattern).
    # Transactional DDL resumes after.
    # ------------------------------------------------------------------
    op.execute(sa.text("COMMIT"))
    op.execute(sa.text("ALTER TYPE argument_status ADD VALUE IF NOT EXISTS 'unpublished'"))

    # ------------------------------------------------------------------
    # Part 2: Create the `argument_status_log` table.
    #
    # ORDERING CONSTRAINT (D-04): CREATE TABLE must come AFTER the ALTER TYPE
    # ADD VALUE above so that the `argument_status` enum type already contains
    # 'unpublished' when PostgreSQL resolves the column definition.
    #
    # The `status` column uses name="argument_status" to bind to the existing
    # PG enum type rather than creating a new shadow type.
    # ------------------------------------------------------------------
    op.create_table(
        "argument_status_log",
        sa.Column("id", sa.Integer, nullable=False),
        sa.Column("argument_id", sa.Integer, sa.ForeignKey("arguments.id"), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pipeline", "draft", "published", "unpublished", name="argument_status"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # ------------------------------------------------------------------
    # Part 3: Backfill — seed one log row per existing argument.
    #
    # Uses each argument's CURRENT status value (status::argument_status)
    # so that a published argument gets a 'published' entry and a draft
    # gets a 'draft' entry. The literal 'created' is NOT used — it is not
    # a valid argument_status enum value (T-22-02 mitigation).
    #
    # Timestamp uses COALESCE(resolved_at, CURRENT_TIMESTAMP) so the seeded
    # row reflects the pipeline resolve timestamp when available (D-07).
    # ------------------------------------------------------------------
    op.execute(sa.text(
        "INSERT INTO argument_status_log (argument_id, status, created_at) "
        "SELECT id, status::argument_status, COALESCE(resolved_at, CURRENT_TIMESTAMP) "
        "FROM arguments"
    ))


def downgrade() -> None:
    op.drop_table("argument_status_log")

    # NOTE: The 'unpublished' value added to the `argument_status` enum type
    # is intentionally NOT removed here. PostgreSQL does not support removing
    # enum values from an existing type — they remain permanently. This is the
    # same discipline used in migration 0008's downgrade for the `side` enum.
