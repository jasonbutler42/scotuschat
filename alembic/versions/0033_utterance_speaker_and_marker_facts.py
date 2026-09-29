"""utterances.speaker_undetermined / is_inaudible_marker / verbatim_text (Phase 53 plan 53-01).

Revision ID: 0033
Revises: 0032
Create Date: 2026-09-29

Adds THREE nullable columns to `utterances` and TWO CHECK constraints. Writes
no row of any kind — no UPDATE, no raw-SQL data statement, no backfill.

    utterances.speaker_undetermined — sa.Boolean(), nullable, no
    database-side default. D-05: a fact stored on the utterance at import
    time, read directly from `speakers.json`'s `type` field
    (`_is_unattributed_speaker_type`) — never re-derived later from
    `raw_speaker_label`, a speaker's display name, or utterance text. True
    means the SOURCE itself could not attribute this turn to a participant
    (ConvoKit's own "U"/"unattributed"/"unknown" sentinel types); this is
    orthogonal to `person_id IS NULL`, which can also mean "not yet
    resolved" for an otherwise-ordinary speaker.

    utterances.is_inaudible_marker — sa.Boolean(), nullable, no
    database-side default. D-12/D-15: the stored fact that a row's whole
    turn is the canonical inaudible marker, so the frontend can select the
    D-15 explanation-card copy from data rather than string-matching
    rendered text. Populated by plan 53-02; this migration only adds the
    column so the phase carries exactly one DDL unit.

    utterances.verbatim_text — sa.Text(), nullable. D-10: the verbatim
    source form of a canonicalised whole-turn marker row, kept alongside
    the canonical form written to `utterances.text` so the raw transcript
    wording stays recoverable and auditable. Populated by plan 53-02.

NULL on every one of these three columns means "written before 0033" (or,
for the latter two, "not yet populated by 53-02") — every reader treats
NULL as false/absent, which fails closed: the row keeps flooring UNCERTAIN
exactly as it does today, and the frontend keeps rendering it as an
ordinary row. This follows migration 0030's stated precedent: an ADD
COLUMN default would write a value into every existing row, which is a
backfill, and this project's standing constraint is reseed-don't-migrate
(CLAUDE.md, memory: reseed, do not migrate) — the corpus is reseeded, not
reconciled, so no stored state needs converting.

The frozen D-13 content digest (`api/domain/content_digest.py`,
`compute_utterance_digest`) ignores any row key outside its four frozen
fields (`sequence`, `raw_speaker_label`, `text`, `is_stage_direction`) and
is NOT modified by this migration or this plan — these three new columns
sit entirely outside the digest's frozen contract. Consequence: a database
imported before 0033 keeps every sentinel/marker row's new columns at NULL
until that database is reseeded (the accepted D-10 cost stated in
53-CONTEXT.md).

Two CHECK constraints make the trust branch's assumptions structural
rather than merely conventional:

    ck_utterances_undetermined_unattributed —
    `speaker_undetermined IS NOT TRUE OR (person_id IS NULL AND
    is_stage_direction = false)`. A row flagged as source-undetermined can
    never simultaneously carry a resolved person_id or be a stage
    direction. Every existing `Utterance.person_id` write in this codebase
    (resolve.py:338, admin_jobs.py:585, admin_dev.py:697, all checked
    during planning) keys its UPDATE on a non-NULL `raw_speaker_label`,
    and a sentinel row's `raw_speaker_label` is always NULL (D-05) — so no
    existing write path can violate this constraint; SQL equality never
    matches a NULL label.

    ck_utterances_inaudible_marker_not_stage —
    `is_inaudible_marker IS NOT TRUE OR is_stage_direction = false`. D-04:
    a whole-turn inaudible marker with a known speaker is a transcription
    failure, not a room event, and must never be stored as a stage
    direction.

downgrade() drops both CHECK constraints by name (Alembic's check-kind
constraint drop), then drops the three columns in reverse declaration
order. No data transformation in either direction.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0033"
down_revision: str = "0032"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UNDETERMINED_CONSTRAINT_NAME = "ck_utterances_undetermined_unattributed"
INAUDIBLE_CONSTRAINT_NAME = "ck_utterances_inaudible_marker_not_stage"


def upgrade() -> None:
    op.add_column(
        "utterances",
        sa.Column("speaker_undetermined", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "utterances",
        sa.Column("is_inaudible_marker", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "utterances",
        sa.Column("verbatim_text", sa.Text(), nullable=True),
    )
    op.create_check_constraint(
        UNDETERMINED_CONSTRAINT_NAME,
        "utterances",
        "speaker_undetermined IS NOT TRUE OR (person_id IS NULL AND is_stage_direction = false)",
    )
    op.create_check_constraint(
        INAUDIBLE_CONSTRAINT_NAME,
        "utterances",
        "is_inaudible_marker IS NOT TRUE OR is_stage_direction = false",
    )


def downgrade() -> None:
    op.drop_constraint(INAUDIBLE_CONSTRAINT_NAME, "utterances", type_="check")
    op.drop_constraint(UNDETERMINED_CONSTRAINT_NAME, "utterances", type_="check")
    op.drop_column("utterances", "verbatim_text")
    op.drop_column("utterances", "is_inaudible_marker")
    op.drop_column("utterances", "speaker_undetermined")
