"""Fold Person's Phase 38 legacy review flag into the unified review record (Phase 49).

Revision ID: 0029
Revises: 0028
Create Date: 2026-08-23

Five ordered steps (49-02-PLAN.md, D-08; operator-confirmed at this plan's
checkpoint decision — the drop half below is one-way and no reverse-
derivation is attempted on downgrade, matching migration 0027's precedent):

    1. ADD COLUMN people.review_state — reuses the EXISTING `review_state`
       PG enum type migration 0028 already minted (`create_type=False`;
       never re-create the type). NOT NULL, server_default='unreviewed'.
       This is the SAME shared type `argument_participants.review_state`
       uses (D-09 — one vocabulary, not two lookalikes).
    2. ADD COLUMN people.provenance_metadata — nullable JSONB, the durable
       extraction/migration audit trail that replaces
       `name_extraction_metadata`.
    3. One set-based UPDATE: rows previously flagged
       `name_needs_review = true` become `review_state = 'needs_review'` —
       the single deterministic legacy mapping the design note's backfill
       table calls for (49-CONTEXT.md "Claude's Discretion"). No other
       derivation is performed — every other pre-existing row keeps the
       `review_state` server_default of 'unreviewed' PostgreSQL applies to
       existing rows as part of step 1's ADD COLUMN itself.
    4. One set-based UPDATE: `name_extraction_metadata` carries straight
       across into `provenance_metadata` for every row where it is not
       NULL — a plain column carry, no reshaping of the JSON.
    5. Two DROP COLUMN calls removing `people.name_needs_review` and
       `people.name_extraction_metadata` — REVIEW-05's no-parallel-
       mechanism requirement means these two Phase 38 names must not
       survive anywhere outside migration history once this migration
       lands (api/tests/test_legacy_review_mechanism_removed.py asserts
       this structurally).

Reversibility: ONE-WAY. The data in the two dropped columns cannot be
recovered by downgrade() — this is the same class of loss migration 0027's
downgrade already accepted for its own enum-expansion half. downgrade()
re-adds `people.name_needs_review` (Boolean, NOT NULL, server_default
false — its exact original nullability/default from migration 0022) and
`people.name_extraction_metadata` (nullable JSONB), then drops
`provenance_metadata` and `review_state`. It does NOT attempt to
reverse-derive the boolean from `review_state`, or reconstruct
`name_extraction_metadata` from `provenance_metadata` — stated explicitly
below, matching migration 0027's downgrade note. `operator_confirmed`,
`operator_edited`, and `unreviewed` all collapse onto a single boolean, so
any derived value would be a fabrication, not a recovery: a downgraded
database has no legacy review data at all, and must re-derive it from a
fresh extraction pass if it is ever needed (49-CONTEXT.md D-08, this plan's
resolved checkpoint decision).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0029"
down_revision: str = "0028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. people.review_state — reuse the EXISTING review_state PG enum
    #    type minted by migration 0028; never re-create it (create_type=
    #    False). Same type as argument_participants.review_state (D-09).
    # ------------------------------------------------------------------
    review_state_enum = postgresql.ENUM(
        "unreviewed", "needs_review", "operator_confirmed", "operator_edited",
        name="review_state",
        create_type=False,
    )
    op.add_column(
        "people",
        sa.Column(
            "review_state",
            review_state_enum,
            nullable=False,
            server_default="unreviewed",
        ),
    )

    # ------------------------------------------------------------------
    # 2. people.provenance_metadata — durable extraction/migration audit
    #    trail, replacing name_extraction_metadata.
    # ------------------------------------------------------------------
    op.add_column(
        "people",
        sa.Column("provenance_metadata", postgresql.JSONB(), nullable=True),
    )

    # ------------------------------------------------------------------
    # 3. Single deterministic legacy mapping (49-CONTEXT.md "Claude's
    #    Discretion" backfill table): a row previously flagged for name
    #    review becomes review_state = 'needs_review'. No other
    #    derivation — every other row keeps the 'unreviewed' default step
    #    1 already applied.
    # ------------------------------------------------------------------
    op.execute(
        sa.text(
            "UPDATE people SET review_state = 'needs_review' "
            "WHERE name_needs_review = true"
        )
    )

    # ------------------------------------------------------------------
    # 4. Straight carry of the extraction envelope — no reshaping.
    # ------------------------------------------------------------------
    op.execute(
        sa.text(
            "UPDATE people SET provenance_metadata = name_extraction_metadata "
            "WHERE name_extraction_metadata IS NOT NULL"
        )
    )

    # ------------------------------------------------------------------
    # 5. Drop the two Phase 38 columns — REVIEW-05's no-parallel-mechanism
    #    requirement. Order: flag, then envelope (reverse of migration
    #    0022's own add order).
    # ------------------------------------------------------------------
    op.drop_column("people", "name_needs_review")
    op.drop_column("people", "name_extraction_metadata")


def downgrade() -> None:
    # Re-add both Phase 38 columns with their ORIGINAL nullability/default
    # from migration 0022. NOTE: this does NOT attempt to reverse-derive
    # name_needs_review from review_state, or reconstruct
    # name_extraction_metadata from provenance_metadata — operator_
    # confirmed, operator_edited, and unreviewed all collapse onto a
    # single boolean, so any derived value would be fabricated rather than
    # recovered (49-CONTEXT.md D-08, this plan's resolved checkpoint
    # decision; matches migration 0027's downgrade note for its own
    # one-way half). A downgraded database therefore has no legacy review
    # data at all.
    op.add_column(
        "people",
        sa.Column(
            "name_needs_review",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "people",
        sa.Column("name_extraction_metadata", postgresql.JSONB(), nullable=True),
    )
    op.drop_column("people", "provenance_metadata")
    op.drop_column("people", "review_state")
