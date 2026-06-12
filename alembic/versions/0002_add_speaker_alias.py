"""Add speaker_alias table.

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-12

Adds the speaker_alias table:
  - Maps raw/normalized speaker labels to a resolved person_id
  - Unique constraint on normalized_label prevents duplicate alias entries
  - Index on normalized_label for fast lookup during speaker resolution
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Table 11: speaker_alias
    # Maps normalized speaker labels to resolved people rows.
    # Unique constraint on normalized_label prevents duplicate aliases.
    # ------------------------------------------------------------------
    op.create_table(
        "speaker_alias",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("normalized_label", sa.String(300), nullable=False),
        sa.Column("person_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["person_id"], ["people.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("normalized_label", name="uq_speaker_alias_label"),
    )
    op.create_index(
        "ix_speaker_alias_normalized_label",
        "speaker_alias",
        ["normalized_label"],
    )


def downgrade() -> None:
    op.drop_index("ix_speaker_alias_normalized_label", table_name="speaker_alias")
    op.drop_table("speaker_alias")
