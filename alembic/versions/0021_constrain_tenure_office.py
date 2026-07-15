"""Constrain normalized tenure offices to chief or associate.

Revision ID: 0021
Revises: 0020
Create Date: 2026-07-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0021"
down_revision: str = "0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONSTRAINT_NAME = "ck_court_tenures_office"


def upgrade() -> None:
    invalid_count = op.get_bind().execute(
        sa.text(
            "SELECT COUNT(*) FROM court_tenures "
            "WHERE office IS NULL OR office NOT IN ('chief', 'associate')"
        )
    ).scalar_one()
    if invalid_count:
        raise RuntimeError(
            f"Cannot constrain court_tenures.office: {invalid_count} unresolved row(s). "
            "Run scripts/migrate_tenure_offices.py dry-run and explicit execution first."
        )

    op.create_check_constraint(
        CONSTRAINT_NAME,
        "court_tenures",
        "office IN ('chief', 'associate')",
    )
    op.alter_column(
        "court_tenures",
        "office",
        existing_type=sa.String(length=100),
        existing_nullable=True,
        nullable=False,
    )


def downgrade() -> None:
    op.drop_constraint(CONSTRAINT_NAME, "court_tenures", type_="check")
    op.alter_column(
        "court_tenures",
        "office",
        existing_type=sa.String(length=100),
        existing_nullable=False,
        nullable=True,
    )
