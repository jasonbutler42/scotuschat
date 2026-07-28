"""Add court_tenures.reason_left, constrained to retired/died/promoted (Phase 39 D-01/D-02).

Revision ID: 0024
Revises: 0023
Create Date: 2026-07-28

Migration 0016 ("Add people.birthdate") explicitly deferred this column
("CourtTenure 'reason left the bench' — UI renders a disabled placeholder
input with no backing column; deferred to a future phase") — this migration
is that future phase's fulfillment.

Unlike migration 0021's office CHECK constraint (which is paired with an
`alter_column(nullable=False)` step because every tenure MUST have an
office), reason_left stays nullable PERMANENTLY (D-02): an open/active
tenure (end_date IS NULL) never has a reason, and a handful of historical
rows have a genuinely blank source value. There is therefore no
`alter_column(nullable=False)` step here and no preflight `SELECT COUNT(*)`
guard — the column starts NULL on every existing row, which the
`IS NULL OR ...` constraint accepts by construction.

Downgrade: drops the CHECK constraint, then the column.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0024"
down_revision: Union[str, None] = "0023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONSTRAINT_NAME = "ck_court_tenures_reason_left"


def upgrade() -> None:
    op.add_column(
        "court_tenures",
        sa.Column(
            "reason_left",
            sa.String(length=50),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        CONSTRAINT_NAME,
        "court_tenures",
        "reason_left IS NULL OR reason_left IN ('retired', 'died', 'promoted')",
    )


def downgrade() -> None:
    op.drop_constraint(CONSTRAINT_NAME, "court_tenures", type_="check")
    op.drop_column("court_tenures", "reason_left")
