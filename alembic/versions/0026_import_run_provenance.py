"""Provenance foundation: import_run replaces pipeline_runs (Phase 47).

Revision ID: 0026
Revises: 0025
Create Date: 2026-08-17

Phase 47 (D-01, D-02, D-05): clean-rebuild migration generalizing
`pipeline_runs` into `import_run` as the single lineage backbone. The project
database is disposable (D-01, operator-confirmed) — no in-migration
`strategy -> source/method` backfill translation is performed; go-forward
provenance is stamped by each writer at row-creation time (D-02).

In order:
    1. Create the two brand-new closed-vocabulary PG enum types
       (`import_source`, `import_method`) via the DO-block-guarded
       `CREATE TYPE` idiom (migration 0003).
    2. Rename `pipeline_run_status` -> `import_run_status` in place — its
       five values (pending/running/completed/failed/needs_review) are
       unchanged, so a rename is correct, not a drop/create.
    3. TRUNCATE `utterances, pipeline_runs` (authorized by D-01 — the DB is
       disposable and Phase 47's later plans re-seed it) then DROP
       `pipeline_runs` (CASCADE removes utterances' now-dangling FK
       reference along with it if any remained).
    4. Create `import_run` fresh with the full column list: the unchanged
       columns from `PipelineRun` (id, argument_id, step, status,
       created_at, completed_at, failure_reason, pdf_path, pdf_url,
       prompt_version) plus the new `source`/`method` (NOT NULL, no
       default — D-02, every writer declares provenance explicitly) and
       `external_id` (nullable dual-write of the ConvoKit conversation id
       for corpus rows — RESEARCH.md Pitfall 1, `Argument.oyez_transcript_id`
       is untouched).
    5. Rename `utterances.pipeline_run_id` -> `import_run_id`, its index,
       and repoint its FK at `import_run.id`.
    6. Drop `utterances.strategy` (D-05) — redundant now that provenance is
       declared once on the parent `import_run` row.

`downgrade()` mirrors this exactly in reverse. Re-adding `utterances.strategy`
is nullable (not NOT NULL) — D-05 notes there is no re-population source for
historical values.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0026"
down_revision: str = "0025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Brand-new closed-vocabulary PG enum types (DO-block guarded —
    #    migration 0003's idiom). CREATE TYPE has no IF NOT EXISTS clause
    #    in any PG version, so pg_type is checked manually.
    # ------------------------------------------------------------------
    conn = op.get_bind()
    for type_name, ddl in [
        (
            "import_source",
            "CREATE TYPE import_source AS ENUM "
            "('operator', 'corpus', 'pdf_pipeline', 'seed')",
        ),
        (
            "import_method",
            "CREATE TYPE import_method AS ENUM "
            "('manual', 'direct', 'normalized', 'rule_based', 'llm_corrective')",
        ),
    ]:
        exists = conn.execute(
            sa.text("SELECT 1 FROM pg_type WHERE typname = :n"), {"n": type_name}
        ).fetchone()
        if not exists:
            conn.execute(sa.text(ddl))

    import_source = postgresql.ENUM(
        "operator", "corpus", "pdf_pipeline", "seed",
        name="import_source",
        create_type=False,
    )
    import_method = postgresql.ENUM(
        "manual", "direct", "normalized", "rule_based", "llm_corrective",
        name="import_method",
        create_type=False,
    )

    # ------------------------------------------------------------------
    # 2. In-place enum rename — pipeline_run_status's 5 values are
    #    unchanged, so a straight rename, no CREATE/DROP TYPE needed.
    # ------------------------------------------------------------------
    op.execute(sa.text("ALTER TYPE pipeline_run_status RENAME TO import_run_status"))
    import_run_status = postgresql.ENUM(
        "pending", "running", "completed", "failed", "needs_review",
        name="import_run_status",
        create_type=False,
    )

    # ------------------------------------------------------------------
    # 3. Clean rebuild (D-01): the disposable DB is truncated, not
    #    backfilled, then pipeline_runs is dropped outright.
    # ------------------------------------------------------------------
    op.execute(sa.text("TRUNCATE TABLE utterances, pipeline_runs CASCADE"))
    # utterances.pipeline_run_id's FK constraint must go before the table it
    # references — op.drop_table has no CASCADE option, and a bare DROP TABLE
    # fails with DependentObjectsStillExistError otherwise.
    op.drop_constraint(
        "utterances_pipeline_run_id_fkey", "utterances", type_="foreignkey"
    )
    op.drop_table("pipeline_runs")

    # ------------------------------------------------------------------
    # 4. Create import_run fresh with the full target column list.
    # ------------------------------------------------------------------
    op.create_table(
        "import_run",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("argument_id", sa.Integer(), nullable=False),
        sa.Column("step", sa.String(50), nullable=False),
        sa.Column("status", import_run_status, nullable=False, server_default="pending"),
        sa.Column("source", import_source, nullable=False),
        sa.Column("method", import_method, nullable=False),
        sa.Column("external_id", sa.String(50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("pdf_path", sa.String(500), nullable=True),
        sa.Column("pdf_url", sa.String(1000), nullable=True),
        sa.Column("prompt_version", sa.String(50), nullable=True),
        sa.ForeignKeyConstraint(["argument_id"], ["arguments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ------------------------------------------------------------------
    # 5. Repoint utterances at import_run.
    # ------------------------------------------------------------------
    op.alter_column(
        "utterances",
        "pipeline_run_id",
        new_column_name="import_run_id",
        existing_type=sa.Integer(),
        existing_nullable=False,
    )
    op.execute(
        sa.text(
            "ALTER INDEX ix_utterances_pipeline_run_id "
            "RENAME TO ix_utterances_import_run_id"
        )
    )
    # 6. Drop the now-redundant per-utterance strategy column (D-05).
    op.drop_column("utterances", "strategy")

    op.create_foreign_key(
        "utterances_import_run_id_fkey",
        "utterances",
        "import_run",
        ["import_run_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "utterances_import_run_id_fkey", "utterances", type_="foreignkey"
    )
    op.add_column(
        "utterances",
        sa.Column("strategy", sa.String(100), nullable=True),
    )
    op.execute(
        sa.text(
            "ALTER INDEX ix_utterances_import_run_id "
            "RENAME TO ix_utterances_pipeline_run_id"
        )
    )
    op.alter_column(
        "utterances",
        "import_run_id",
        new_column_name="pipeline_run_id",
        existing_type=sa.Integer(),
        existing_nullable=False,
    )

    op.drop_table("import_run")

    # Rename the status type back BEFORE the table that references it is
    # recreated below (mirror of upgrade()'s ordering, reversed).
    op.execute(sa.text("ALTER TYPE import_run_status RENAME TO pipeline_run_status"))
    pipeline_run_status = postgresql.ENUM(
        "pending", "running", "completed", "failed", "needs_review",
        name="pipeline_run_status",
        create_type=False,
    )
    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("argument_id", sa.Integer(), nullable=False),
        sa.Column("step", sa.String(50), nullable=False),
        sa.Column(
            "status", pipeline_run_status, nullable=False, server_default="pending"
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
    op.create_foreign_key(
        "utterances_pipeline_run_id_fkey",
        "utterances",
        "pipeline_runs",
        ["pipeline_run_id"],
        ["id"],
    )

    op.execute(sa.text("DROP TYPE IF EXISTS import_source"))
    op.execute(sa.text("DROP TYPE IF EXISTS import_method"))
