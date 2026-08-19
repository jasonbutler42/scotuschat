"""Trust tier column + candidate status (Phase 48).

Revision ID: 0027
Revises: 0026
Create Date: 2026-08-19

Five ordered steps (48-RESEARCH.md § "Migration Mechanics", Pitfall 5):

    1. COMMIT Alembic's implicit transaction, then
       ALTER TYPE argument_status ADD VALUE IF NOT EXISTS 'candidate' — PG
       forbids ADD VALUE inside a transaction block (same discipline as
       migration 0012's 'unpublished' expansion).
    2. UPDATE arguments SET status = 'candidate' WHERE status = 'pipeline'
       (D-24) — must come after step 1 so the value already exists on the
       enum type. This is the only place 'pipeline' is retired from live
       rows; PostgreSQL cannot drop the enum value itself, so 'pipeline'
       stays defined but dead from this point forward.
    3. CREATE TYPE trust_tier AS ENUM (...) via the pg_type existence-guard
       idiom migration 0026 established — independent of steps 1/2, no
       ordering dependency on the argument_status type.
    4. ADD COLUMN arguments.trust_tier, NOT NULL, server_default='uncertain'.
       No separate backfill UPDATE — PostgreSQL applies a non-volatile
       server_default to every existing row as part of ADD COLUMN itself
       (documented PG behavior since v11). This matches the operator's
       explicit lean recorded in 48-CONTEXT.md's "Claude's Discretion"
       section: the project DB is disposable and gets reset-to-fixture
       repeatedly during development, so no in-migration derivation is
       performed — the fail-closed default is the backfill.
    5. ADD COLUMN argument_status_log.override_reason (nullable text) and
       .trust_tier_at_transition (nullable trust_tier enum) (D-15) — must
       come after step 3 since these columns reference the trust_tier type.
       Both nullable: every non-override status transition (DRAFT,
       PUBLISHED, UNPUBLISHED, CANDIDATE-at-birth) legitimately carries
       NULL here.

downgrade() mirrors steps 5, 4, 3 in reverse (three drop_column calls, then
DROP TYPE trust_tier) and flips status='pipeline' WHERE status='candidate'.
It does NOT attempt to remove the 'candidate' enum value from
argument_status — PostgreSQL cannot remove enum values once added, so that
part of upgrade() is genuinely one-way (48-CONTEXT.md D-01/D-06/D-15 each
record this migration as "Reversibility: one-way").
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0027"
down_revision: str = "0026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Expand argument_status with 'candidate'. ADD VALUE cannot run
    #    inside a transaction block — commit Alembic's implicit transaction
    #    first (same discipline as migrations 0008 and 0012).
    # ------------------------------------------------------------------
    op.execute(sa.text("COMMIT"))
    op.execute(sa.text("ALTER TYPE argument_status ADD VALUE IF NOT EXISTS 'candidate'"))

    # ------------------------------------------------------------------
    # 2. Flip any existing 'pipeline' rows to 'candidate' (D-24). Must run
    #    after step 1 so the target value already exists on the enum type.
    # ------------------------------------------------------------------
    op.execute(sa.text("UPDATE arguments SET status = 'candidate' WHERE status = 'pipeline'"))

    # ------------------------------------------------------------------
    # 3. New enum type trust_tier — independent of argument_status, no
    #    ordering dependency on steps 1/2 (Pitfall 5). pg_type
    #    existence-guard idiom from migration 0026.
    # ------------------------------------------------------------------
    conn = op.get_bind()
    exists = conn.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = :n"), {"n": "trust_tier"}
    ).fetchone()
    if not exists:
        conn.execute(
            sa.text(
                "CREATE TYPE trust_tier AS ENUM "
                "('verified', 'trusted', 'provisional', 'uncertain')"
            )
        )

    trust_tier_enum = postgresql.ENUM(
        "verified", "trusted", "provisional", "uncertain",
        name="trust_tier",
        create_type=False,
    )

    # ------------------------------------------------------------------
    # 4. arguments.trust_tier — NOT NULL, server_default='uncertain'. No
    #    separate backfill UPDATE: PostgreSQL applies the non-volatile
    #    default to every existing row as part of ADD COLUMN.
    # ------------------------------------------------------------------
    op.add_column(
        "arguments",
        sa.Column(
            "trust_tier",
            trust_tier_enum,
            nullable=False,
            server_default="uncertain",
        ),
    )

    # ------------------------------------------------------------------
    # 5. argument_status_log gains two nullable override columns (D-15).
    #    Must come after step 3 since trust_tier_at_transition references
    #    the trust_tier type.
    # ------------------------------------------------------------------
    op.add_column(
        "argument_status_log",
        sa.Column("override_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "argument_status_log",
        sa.Column(
            "trust_tier_at_transition",
            trust_tier_enum,
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("argument_status_log", "trust_tier_at_transition")
    op.drop_column("argument_status_log", "override_reason")
    op.drop_column("arguments", "trust_tier")
    op.execute(sa.text("DROP TYPE IF EXISTS trust_tier"))
    # NOTE: does NOT attempt to remove 'candidate' from argument_status —
    # PostgreSQL cannot remove enum values once added. The flip below is a
    # best-effort partial reversal of step 2 only.
    op.execute(sa.text("UPDATE arguments SET status = 'pipeline' WHERE status = 'candidate'"))
