"""Argument.slug column + unique constraint (Phase 51 plan 51-02, D-12).

Revision ID: 0031
Revises: 0030
Create Date: 2026-08-28

Adds ONE new nullable column and its unique constraint:

    arguments.slug — sa.String(200), nullable, UNIQUE (constraint name
    `uq_arguments_slug`). Mirrors `cases.slug`'s existing column shape
    (String(200), unique) exactly (api/models/models.py, Case.slug).

D-12: generated once at import via `api.domain.argument_slug.
derive_argument_slug` and never recomputed when a case name is later
edited, so a shared public URL survives an operator correcting a case-name
typo. Nullable (not NOT NULL) because this project reseeds rather than
migrates data (CLAUDE.md, standing "reseed, do not backfill" constraint) —
existing rows get their slug from the next real reseed through the import
path, not from an UPDATE statement in this migration.

Per the project's standing reseed-not-migrate constraint, this migration
contains NO UPDATE, NO raw-SQL data statement, and NO backfill of any
kind. NULL means "no slug minted yet" on every existing row.

D-13's reserved-slug-word rule (a minted slug must never equal the
literal path segment "term", which the `/arguments/term/{year}` route
owns) is enforced entirely in application-layer slug generation
(`api.domain.argument_slug.RESERVED_SLUG_WORDS`) — deliberately NOT as a
database CHECK constraint, matching migration 0030's precedent of keeping
this class of business rule out of the schema layer.

downgrade() drops the unique constraint then the column.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0031"
down_revision: str = "0030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "arguments",
        sa.Column("slug", sa.String(200), nullable=True),
    )
    op.create_unique_constraint(
        "uq_arguments_slug",
        "arguments",
        ["slug"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_arguments_slug", "arguments", type_="unique")
    op.drop_column("arguments", "slug")
