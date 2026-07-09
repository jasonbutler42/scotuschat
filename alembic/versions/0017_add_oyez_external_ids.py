"""Add nullable oyez_* external-ID columns to cases, arguments, people (D-10).

Revision ID: 0017
Revises: 0016
Create Date: 2026-07-09

Adds three nullable external-ID columns so corpus-sourced rows (Cornell
ConvoKit / Oyez supreme-corpus import, Phase 29) can carry their originating
Oyez/ConvoKit identifiers alongside the existing pipeline-native rows:

  - cases.oyez_case_id            VARCHAR(50)  NULL
  - arguments.oyez_transcript_id  VARCHAR(50)  NULL
  - people.oyez_speaker_id        VARCHAR(100) NULL

No backfill is performed — all existing rows remain NULL after this
migration. Only rows created by the historical corpus importer (later
plans in this phase) will populate these columns.

Downgrade: drops all three columns in reverse order (people, arguments, cases).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0017"
down_revision: Union[str, None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cases",
        sa.Column(
            "oyez_case_id",
            sa.String(50),
            nullable=True,
        ),
    )
    op.add_column(
        "arguments",
        sa.Column(
            "oyez_transcript_id",
            sa.String(50),
            nullable=True,
        ),
    )
    op.add_column(
        "people",
        sa.Column(
            "oyez_speaker_id",
            sa.String(100),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("people", "oyez_speaker_id")
    op.drop_column("arguments", "oyez_transcript_id")
    op.drop_column("cases", "oyez_case_id")
