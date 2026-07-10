"""Relax cases.docket_number uniqueness to (docket_number, term_year) (Phase 29 corpus-import gap).

Revision ID: 0018
Revises: 0017
Create Date: 2026-07-10

Historical SCOTUS docket numbers recycle across October Terms (e.g. docket
"71" is a distinct, unrelated case in nearly a dozen different terms between
1955 and 1970) -- unlike modern docket numbers, which already embed the term
(e.g. "23-1234") and are naturally globally unique. The original bare
UNIQUE(docket_number) constraint assumed global uniqueness and would either
reject or silently conflate distinct historical cases sharing a docket
number.

Drops the single-column UNIQUE(docket_number) constraint and replaces it
with a composite UNIQUE(docket_number, term_year). Modern PDF-ingested cases
are unaffected (their docket numbers are unique on their own, term_year or
not); the historical corpus importer now dedups new Cases by the stable
oyez_case_id when present, falling back to (docket_number, term_year) --
see pipeline/commands/import_convokit.py's _get_or_create_case.

No data migration/backfill needed -- this only changes which combination of
columns the DB enforces as unique; no existing row's data changes.

Downgrade: drops the composite constraint and restores the original bare
UNIQUE(docket_number) constraint. Note: downgrading will fail if any two
existing rows share the same docket_number by that point (expected, since
the whole point of this migration is to allow that).
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0018"
down_revision: Union[str, None] = "0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("cases_docket_number_key", "cases", type_="unique")
    op.create_unique_constraint(
        "uq_cases_docket_number_term_year", "cases", ["docket_number", "term_year"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_cases_docket_number_term_year", "cases", type_="unique")
    op.create_unique_constraint("cases_docket_number_key", "cases", ["docket_number"])
