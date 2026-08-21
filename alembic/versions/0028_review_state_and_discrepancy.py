"""review_state enum + argument_participants provenance columns + value_discrepancy (Phase 49).

Revision ID: 0028
Revises: 0027
Create Date: 2026-08-21

Three ordered steps (49-01-PLAN.md, D-09/D-10/D-19/D-20; operator-confirmed
at this plan's checkpoint decision — the vocabulary below is permanent from
the moment this migration runs, PostgreSQL has no ALTER TYPE ... DROP VALUE):

    1. CREATE TYPE review_state AS ENUM ('unreviewed', 'needs_review',
       'operator_confirmed', 'operator_edited') via the pg_type
       existence-guard idiom migrations 0026/0027 established. This is a
       ONE-WAY door: once this type exists, none of its four values can
       ever be renamed or removed — only ADD VALUE is available for a
       future fifth state. The same permanent-vocabulary constraint that
       left argument_status's 'pipeline' value dead-but-permanent
       (api/models/models.py:344) after migration 0027's own
       new-column-and-migrate cycle.
    2. ADD COLUMN three times on argument_participants: review_state (the
       new enum, NOT NULL, server_default='unreviewed'), source (reuses the
       EXISTING import_source PG type verbatim — no new enum, no mapping
       layer, D-20), method (reuses the EXISTING import_method PG type
       verbatim, D-20). No separate backfill UPDATE — PostgreSQL applies
       the non-volatile server_default to every existing row as part of
       ADD COLUMN itself (documented PG behavior since v11; same discipline
       as migration 0027 step 4). source/method are nullable — not every
       existing participant row has known provenance.
    3. CREATE TABLE value_discrepancy — a NEW table, unrelated to the
       legacy admin_jobs.discrepancies JSONB blob (D-14). Natural key is
       (target_type, target_id, field, import_run_id) per D-13, but this is
       NOT enforced as a UNIQUE constraint: D-15 states a re-import can
       legitimately disagree on more than one field, and a repeat run must
       be able to record a fresh row alongside an already-resolved one. A
       non-unique index on (target_type, target_id, resolved_at) lets the
       review queue ask "does this row have an open discrepancy" without a
       full scan.

downgrade() mirrors this in reverse: drops value_discrepancy, drops the
three argument_participants columns, drops the review_state type. It does
not attempt to reverse-derive anything — dropping the type is safe exactly
because upgrade() never wrote review_state data anywhere outside this
migration's own new columns.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0028"
down_revision: str = "0027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. New closed-vocabulary PG enum type review_state. pg_type
    #    existence-guard idiom (migrations 0026/0027) — CREATE TYPE has no
    #    IF NOT EXISTS clause in any PG version.
    #
    #    ONE-WAY DOOR: PostgreSQL cannot drop an enum value once added.
    #    These four values are permanent for the life of this database.
    # ------------------------------------------------------------------
    conn = op.get_bind()
    exists = conn.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = :n"), {"n": "review_state"}
    ).fetchone()
    if not exists:
        conn.execute(
            sa.text(
                "CREATE TYPE review_state AS ENUM "
                "('unreviewed', 'needs_review', 'operator_confirmed', 'operator_edited')"
            )
        )

    review_state_enum = postgresql.ENUM(
        "unreviewed", "needs_review", "operator_confirmed", "operator_edited",
        name="review_state",
        create_type=False,
    )

    # Existing PG enum types reused verbatim (D-20) — no new enum, no
    # mapping layer, because derive_tier already keys on this vocabulary.
    import_source_enum = postgresql.ENUM(
        "operator", "corpus", "pdf_pipeline", "seed",
        name="import_source",
        create_type=False,
    )
    import_method_enum = postgresql.ENUM(
        "manual", "direct", "normalized", "rule_based", "llm_corrective",
        name="import_method",
        create_type=False,
    )

    # ------------------------------------------------------------------
    # 2. argument_participants gains review_state/source/method. No
    #    backfill UPDATE — PostgreSQL applies the non-volatile
    #    server_default to every existing row as part of ADD COLUMN.
    # ------------------------------------------------------------------
    op.add_column(
        "argument_participants",
        sa.Column(
            "review_state",
            review_state_enum,
            nullable=False,
            server_default="unreviewed",
        ),
    )
    op.add_column(
        "argument_participants",
        sa.Column("source", import_source_enum, nullable=True),
    )
    op.add_column(
        "argument_participants",
        sa.Column("method", import_method_enum, nullable=True),
    )

    # ------------------------------------------------------------------
    # 3. New table value_discrepancy — per-value operator-review
    #    bookkeeping (D-13), NOT the legacy admin_jobs.discrepancies JSONB
    #    blob (D-14). No UNIQUE constraint on the natural key — a repeat
    #    import can legitimately disagree on more than one field (D-15).
    # ------------------------------------------------------------------
    op.create_table(
        "value_discrepancy",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("target_type", sa.String(40), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("field", sa.String(60), nullable=False),
        sa.Column("import_run_id", sa.Integer(), nullable=True),
        sa.Column("incoming_value", sa.Text(), nullable=True),
        sa.Column("existing_value", sa.Text(), nullable=True),
        sa.Column("incoming_source", import_source_enum, nullable=True),
        sa.Column("incoming_method", import_method_enum, nullable=True),
        sa.Column("existing_source", import_source_enum, nullable=True),
        sa.Column("existing_method", import_method_enum, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["import_run_id"], ["import_run.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_value_discrepancy_target",
        "value_discrepancy",
        ["target_type", "target_id", "resolved_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_value_discrepancy_target", table_name="value_discrepancy")
    op.drop_table("value_discrepancy")
    op.drop_column("argument_participants", "method")
    op.drop_column("argument_participants", "source")
    op.drop_column("argument_participants", "review_state")
    op.execute(sa.text("DROP TYPE IF EXISTS review_state"))
