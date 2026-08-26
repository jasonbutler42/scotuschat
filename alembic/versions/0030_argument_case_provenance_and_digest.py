"""Argument/Case provenance columns, participant pairing key, content digest (Phase 50).

Revision ID: 0030
Revises: 0029
Create Date: 2026-08-26

Six new nullable columns (50-01-PLAN.md Task 1, OQ-1/D-04/D-13; frozen at
this plan's Task 0 checkpoint decision — `freeze-as-proposed`):

    1. argument_participants.oyez_speaker_id — sa.String(50), nullable.
       D-04's explicit re-import pairing key: the ConvoKit speaker id this
       participant row was resolved from. Width matches
       Person.oyez_speaker_id and ImportRun.external_id, which carry the
       same ConvoKit id vocabulary.
    2. import_run.content_digest — sa.String(64), nullable. D-13's frozen
       lowercase sha256 hex digest of an argument's ordered utterance
       content, carried by step="parse" runs only (OQ-3).
    3-4. arguments.source / arguments.method — reuse the EXISTING
       import_source / import_method PG enum types verbatim
       (create_type=False, exactly as migration 0028 reuses them for
       argument_participants), nullable. OQ-1.
    5-6. cases.source / cases.method — same reused enum types, nullable.
       OQ-1.

Per D-15/D-16 and the project's standing reseed-not-migrate constraint,
this migration contains NO UPDATE, NO raw-SQL data statement, and NO
server_default-driven backfill. NULL means unknown provenance/pairing/
digest on every one of the six columns, and the gate plan 50-02 owns
fails closed on it.

downgrade() drops all six columns in reverse declaration order. No enum
type is created or dropped here — all four enum-typed columns reuse
review_state/import_source/import_method types that already exist.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0030"
down_revision: str = "0029"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing PG enum types reused verbatim (OQ-1) — no new enum, no
    # mapping layer, matching migration 0028's own reuse of these same
    # two types for argument_participants.source/method.
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

    # 1. D-04 pairing key.
    op.add_column(
        "argument_participants",
        sa.Column("oyez_speaker_id", sa.String(50), nullable=True),
    )

    # 2. D-13 content digest.
    op.add_column(
        "import_run",
        sa.Column("content_digest", sa.String(64), nullable=True),
    )

    # 3-4. OQ-1: Argument provenance.
    op.add_column(
        "arguments",
        sa.Column("source", import_source_enum, nullable=True),
    )
    op.add_column(
        "arguments",
        sa.Column("method", import_method_enum, nullable=True),
    )

    # 5-6. OQ-1: Case provenance.
    op.add_column(
        "cases",
        sa.Column("source", import_source_enum, nullable=True),
    )
    op.add_column(
        "cases",
        sa.Column("method", import_method_enum, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cases", "method")
    op.drop_column("cases", "source")
    op.drop_column("arguments", "method")
    op.drop_column("arguments", "source")
    op.drop_column("import_run", "content_digest")
    op.drop_column("argument_participants", "oyez_speaker_id")
