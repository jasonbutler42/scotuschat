"""Make arguments.question_number nullable, drop its server default.

Revision ID: 0019
Revises: 0018
Create Date: 2026-07-11

Alters `arguments.question_number` from NOT NULL (server default of 1) to
nullable with no server default. Product decision (confirmed 2026-07-11):
blank question_number means NULL / "unknown", full parity with argued_date
(migration 0011 made argued_date nullable for the identical reason). Closes
the AEDIT-04 gap from 30.1-UAT.md test 3, where blanking the Question number
in the Argument Details card and saving raised an unhandled asyncpg
IntegrityError instead of persisting NULL.

No data loss: existing rows keep their current integer question_number
values unchanged — only the column's NOT NULL constraint and server default
are altered.

The existing unique constraint uq_arguments_source_docket_question on
(source_docket, question_number) now also permits multiple rows sharing a
source_docket with a NULL question_number, under standard SQL NULL-distinctness
semantics (NULL != NULL for unique index purposes). This is accepted per the
product decision, mirroring the identical NULL semantics migration 0011
already documented for source_docket.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0019"
down_revision: Union[str, None] = "0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make question_number nullable and drop its server default (was '1').
    # Existing rows retain their current values — no backfill needed.
    op.alter_column(
        "arguments",
        "question_number",
        nullable=True,
        server_default=None,
    )


def downgrade() -> None:
    # CR-03-style ordering (mirrors migration 0011's argued_date downgrade):
    # backfill NULLs BEFORE tightening to NOT NULL so the ALTER cannot fail.
    op.execute("UPDATE arguments SET question_number = 1 WHERE question_number IS NULL")
    op.alter_column(
        "arguments",
        "question_number",
        nullable=False,
        server_default="1",
    )
