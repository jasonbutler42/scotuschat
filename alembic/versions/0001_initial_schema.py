"""Initial schema — all 10 tables.

Revision ID: 0001
Revises:
Create Date: 2026-06-11

Creates all 10 tables in FK-dependency order:
  1. roles (no FKs)
  2. people (FK: roles)
  3. court_tenures (FK: people)
  4. cases (no FKs)
  5. arguments (no FKs)
  6. case_arguments (FK: cases, arguments)
  7. case_appearances (FK: cases, people, roles)
  8. argument_participants (FK: arguments, people)
  9. pipeline_runs (FK: arguments)
  10. utterances (FK: arguments, pipeline_runs, people)

Also creates the PostgreSQL enum types: side, pipeline_run_status.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM as PgENUM

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Create PostgreSQL enum types before the tables that reference them.
    # Use raw SQL with IF NOT EXISTS — more reliable than sa.Enum.create()
    # with checkfirst=True, which doesn't work correctly via asyncpg.
    # ------------------------------------------------------------------
    # PostgreSQL has no CREATE TYPE IF NOT EXISTS; use a DO block instead.
    op.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE side AS ENUM ('BENCH', 'ADVOCATE', 'UNKNOWN');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """))
    op.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE pipeline_run_status
                AS ENUM ('pending', 'running', 'completed', 'failed', 'needs_review');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """))

    # ------------------------------------------------------------------
    # Table 1: roles
    # ------------------------------------------------------------------
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # ------------------------------------------------------------------
    # Table 2: people
    # ------------------------------------------------------------------
    op.create_table(
        "people",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(300), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ------------------------------------------------------------------
    # Table 3: court_tenures
    # ------------------------------------------------------------------
    op.create_table(
        "court_tenures",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("person_id", sa.Integer(), nullable=False),
        sa.Column("seat", sa.String(100), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["person_id"], ["people.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ------------------------------------------------------------------
    # Table 4: cases
    # ------------------------------------------------------------------
    op.create_table(
        "cases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("docket_number", sa.String(50), nullable=False),
        sa.Column("docket_number_norm", sa.String(50), nullable=False),
        sa.Column("case_name", sa.String(500), nullable=False),
        sa.Column("term_year", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(200), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("docket_number"),
        sa.UniqueConstraint("slug"),
    )

    # ------------------------------------------------------------------
    # Table 5: arguments
    # ------------------------------------------------------------------
    op.create_table(
        "arguments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("argued_date", sa.Date(), nullable=False),
        sa.Column("question_number", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ------------------------------------------------------------------
    # Table 6: case_arguments (M:M join — composite PK)
    # ------------------------------------------------------------------
    op.create_table(
        "case_arguments",
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("argument_id", sa.Integer(), nullable=False),
        sa.Column("is_lead", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["argument_id"], ["arguments.id"]),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"]),
        sa.PrimaryKeyConstraint("case_id", "argument_id"),
    )

    # ------------------------------------------------------------------
    # Table 7: case_appearances
    # ------------------------------------------------------------------
    op.create_table(
        "case_appearances",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("person_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"]),
        sa.ForeignKeyConstraint(["person_id"], ["people.id"]),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ------------------------------------------------------------------
    # Table 8: argument_participants
    # ------------------------------------------------------------------
    op.create_table(
        "argument_participants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("argument_id", sa.Integer(), nullable=False),
        sa.Column("person_id", sa.Integer(), nullable=True),
        sa.Column("raw_speaker_label", sa.String(200), nullable=False),
        sa.Column("side", PgENUM(name="side", create_type=False), nullable=False),
        sa.ForeignKeyConstraint(["argument_id"], ["arguments.id"]),
        sa.ForeignKeyConstraint(["person_id"], ["people.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ------------------------------------------------------------------
    # Table 9: pipeline_runs
    # ------------------------------------------------------------------
    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("argument_id", sa.Integer(), nullable=False),
        sa.Column("step", sa.String(50), nullable=False),
        sa.Column(
            "status",
            PgENUM(name="pipeline_run_status", create_type=False),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("pdf_path", sa.String(500), nullable=True),
        sa.Column("pdf_url", sa.String(1000), nullable=True),
        sa.Column("strategy", sa.String(100), nullable=True),
        sa.Column("prompt_version", sa.String(50), nullable=True),
        sa.ForeignKeyConstraint(["argument_id"], ["arguments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ------------------------------------------------------------------
    # Table 10: utterances
    # BigInteger PK — could accumulate millions of rows.
    # Unique constraint on (argument_id, pipeline_run_id, sequence) prevents
    # duplicate rows when a pipeline step is re-run.
    # Two indexes for query performance.
    # ------------------------------------------------------------------
    op.create_table(
        "utterances",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("argument_id", sa.Integer(), nullable=False),
        sa.Column("pipeline_run_id", sa.Integer(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("raw_speaker_label", sa.String(200), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("is_stage_direction", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("section_hint", sa.String(50), nullable=True),
        sa.Column(
            "side",
            PgENUM(name="side", create_type=False),
            nullable=False,
            server_default="UNKNOWN",
        ),
        sa.Column("person_id", sa.Integer(), nullable=True),
        sa.Column("strategy", sa.String(100), nullable=False),
        sa.ForeignKeyConstraint(["argument_id"], ["arguments.id"]),
        sa.ForeignKeyConstraint(["person_id"], ["people.id"]),
        sa.ForeignKeyConstraint(["pipeline_run_id"], ["pipeline_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "argument_id", "pipeline_run_id", "sequence",
            name="uq_utterance_arg_run_seq",
        ),
    )
    op.create_index("ix_utterances_argument_id", "utterances", ["argument_id"])
    op.create_index("ix_utterances_pipeline_run_id", "utterances", ["pipeline_run_id"])


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_index("ix_utterances_pipeline_run_id", table_name="utterances")
    op.drop_index("ix_utterances_argument_id", table_name="utterances")
    op.drop_table("utterances")
    op.drop_table("pipeline_runs")
    op.drop_table("argument_participants")
    op.drop_table("case_appearances")
    op.drop_table("case_arguments")
    op.drop_table("arguments")
    op.drop_table("cases")
    op.drop_table("court_tenures")
    op.drop_table("people")
    op.drop_table("roles")

    # Drop enum types last (after all tables using them are dropped)
    sa.Enum(name="side").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="pipeline_run_status").drop(op.get_bind(), checkfirst=True)
