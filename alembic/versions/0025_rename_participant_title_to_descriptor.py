"""Rename argument_participants.title to descriptor (Phase 44 D-05).

Revision ID: 0025
Revises: 0024
Create Date: 2026-08-01

Migration 0013 ("Add argument_participants.title...") added this column (Phase 22,
PJOB-13) to hold the advocate's TOC subtitle line (e.g. "Solicitor General"). Phase 44
D-05 renames it to `descriptor` as part of a full-stack rename across the ORM, Pydantic
schemas, services, routers, the pipeline parse writer, and both SvelteKit consumers —
the Resolve table's "Descriptor" column is a generic free-form field, not just a UI
label change over the old "Title" name.

This is a true in-place rename only: `op.alter_column(..., new_column_name=...)`.
No add-column, no drop-column, no data-copy step — every existing row's value is
preserved verbatim. `downgrade()` is the exact mirror.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0025"
down_revision: str = "0024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "argument_participants",
        "title",
        new_column_name="descriptor",
        existing_type=sa.String(length=500),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "argument_participants",
        "descriptor",
        new_column_name="title",
        existing_type=sa.String(length=500),
        existing_nullable=True,
    )
