"""Add bio_text and photo_url columns to people table.

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-17

Adds two nullable columns to the people table to support the People Editor admin UI:
  - bio_text TEXT nullable: operator-provided biography text for the person
  - photo_url VARCHAR(500) nullable: URL to the person's photo (e.g. from Oyez)

Both columns default to NULL. A person with role_id IS NULL OR bio_text IS NULL
OR photo_url IS NULL is considered incomplete (D-04 in Phase 8 CONTEXT.md).
Existing rows are unaffected — they retain NULL values until the operator fills
them in via the admin People Editor.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("people", sa.Column("bio_text", sa.Text(), nullable=True))
    op.add_column("people", sa.Column("photo_url", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("people", "photo_url")
    op.drop_column("people", "bio_text")
