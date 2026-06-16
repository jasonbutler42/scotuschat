"""Add admin_jobs table.

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-15

Adds the admin_jobs table:
  - Tracks operator-initiated pipeline jobs for the v1.1 admin UI
  - status and current_step stored as PG enum types
  - argument_id is a nullable FK to arguments; NULL until ingest creates the row (D-02)
  - discrepancies stored as JSONB for batch fire-and-poll reads (D-03)
  - pdf_url and spaces_key capture full input provenance (D-06)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Create PostgreSQL enum types before the table that uses them.
    # Enum types must exist before the columns referencing them.
    # Use checkfirst=True to handle re-entrant upgrades safely.
    # ------------------------------------------------------------------
    admin_job_status = sa.Enum(
        "pending", "running", "paused", "completed", "failed",
        name="admin_job_status",
    )
    admin_job_step = sa.Enum(
        "ingest", "parse", "resolve",
        name="admin_job_step",
    )
    admin_job_status.create(op.get_bind(), checkfirst=True)
    admin_job_step.create(op.get_bind(), checkfirst=True)

    # ------------------------------------------------------------------
    # Table 12: admin_jobs
    # Tracks operator-initiated pipeline jobs submitted via the admin UI.
    # status: pending → running → completed | failed | paused (D-04)
    # current_step: NULL (not started), ingest, parse, resolve (D-05)
    # argument_id: nullable FK — NULL until ingest creates the argument row (D-02)
    # discrepancies: JSONB — read as a batch during fire-and-poll (D-03)
    # pdf_url / spaces_key: full input provenance (D-06)
    # ------------------------------------------------------------------
    op.create_table(
        "admin_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("status", admin_job_status, nullable=False, server_default="pending"),
        sa.Column("current_step", admin_job_step, nullable=True),
        sa.Column("argument_id", sa.Integer(), nullable=True),
        sa.Column("pdf_url", sa.Text(), nullable=True),
        sa.Column("spaces_key", sa.Text(), nullable=True),
        sa.Column("discrepancies", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["argument_id"], ["arguments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ------------------------------------------------------------------
    # BEFORE UPDATE trigger so updated_at is maintained by the database
    # regardless of whether the caller goes through the ORM or raw SQL.
    # ------------------------------------------------------------------
    op.execute("""
        CREATE OR REPLACE FUNCTION set_admin_jobs_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_admin_jobs_updated_at
        BEFORE UPDATE ON admin_jobs
        FOR EACH ROW EXECUTE FUNCTION set_admin_jobs_updated_at();
    """)


def downgrade() -> None:
    # Drop the trigger and function before dropping the table.
    op.execute("DROP TRIGGER IF EXISTS trg_admin_jobs_updated_at ON admin_jobs")
    op.execute("DROP FUNCTION IF EXISTS set_admin_jobs_updated_at()")
    op.drop_table("admin_jobs")
    op.execute("DROP TYPE IF EXISTS admin_job_status")
    op.execute("DROP TYPE IF EXISTS admin_job_step")
