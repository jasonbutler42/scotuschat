"""people.display_name column + partial unique index on oyez_speaker_id (Phase 52 plan 52-01).

Revision ID: 0032
Revises: 0031
Create Date: 2026-09-25

Adds ONE new nullable column and ONE partial unique index:

    people.display_name — sa.String(300), nullable. Matches full_name's
    column width (String(300)) because display_name is the corpus's own
    word, exactly as full_name is the name parts' word (D-09,
    52-CONTEXT.md). It carries the corpus display form
    (e.g. "Byron R. White") that drives utterance attribution; the bio
    card keeps reading full_name (e.g. "Byron Raymond White") unchanged.

    uq_people_oyez_speaker_id — a PARTIAL unique index on
    people(oyez_speaker_id) WHERE oyez_speaker_id IS NOT NULL. Makes a
    duplicate justice row structurally impossible (JUSTICE-05) while
    tolerating any number of NULL oyez_speaker_id rows (advocates, and
    D-04's Amy Coney Barrett / Ketanji Brown Jackson, who are seated after
    the corpus's 2019 cutoff and so have no corpus speaker id yet).

Nullable (not NOT NULL) because this project reseeds rather than migrates
data (CLAUDE.md, standing "reseed, do not backfill" constraint) — existing
rows get display_name from the next real justice-seed pass through
pipeline/commands/import_justices_csv.py, not from an UPDATE statement in
this migration.

Per the project's standing reseed-not-migrate constraint, this migration
contains NO UPDATE, NO raw-SQL data statement, and NO backfill of any
kind. NULL means "no corpus display form yet" on every existing row.

The `postgresql_where` partial-index predicate has NO PRIOR EXAMPLE
anywhere in this repo's 32 prior migrations (grep across all of
alembic/versions/ for postgresql_where returns zero hits) — a future
reader should not go hunting for a local precedent that does not exist.
The syntax is SQLAlchemy's documented Postgres dialect API
(sqlalchemy.Index / op.create_index with postgresql_where=sa.text(...)),
cross-checked against sqlalchemy.org's postgresql dialect docs. The
immediately-prior migration (0031_argument_slug.py) supplies the
surrounding nullable-column-plus-unique-constraint shape this migration
copies, but NOT the partial predicate itself — 0031's constraint is a
plain (non-partial) unique constraint.

downgrade() drops the index by name, then drops the column. No data
transformation in either direction.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0032"
down_revision: str = "0031"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "people",
        sa.Column("display_name", sa.String(300), nullable=True),
    )
    op.create_index(
        "uq_people_oyez_speaker_id",
        "people",
        ["oyez_speaker_id"],
        unique=True,
        postgresql_where=sa.text("oyez_speaker_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_people_oyez_speaker_id", table_name="people")
    op.drop_column("people", "display_name")
