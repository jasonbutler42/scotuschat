"""Add Person name-review flag and extraction-metadata provenance; guarded legacy backfill.

Revision ID: 0022
Revises: 0021
Create Date: 2026-07-27

Phase 38 (D-01, D-04, D-10-D-12, D-14-D-18): structured name parts become
the authoritative operator-editable representation of a person going
forward. This migration establishes the durable persistence contract that
every later Phase 38 write path (services, imports, pipeline extraction)
relies on, and safely converts existing full-name-only rows:

  - `people.name_needs_review` BOOLEAN NOT NULL DEFAULT false — durable
    flag surfaced by the People directory's `Name review` filter (D-12) for
    any legacy row this migration could not confidently split.
  - `people.name_extraction_metadata` JSONB NULL — persists independently
    of any operator-edited name part (D-15). Used here to record this
    migration's own split decision/reason/confidence for every row it
    examined; later pipeline/import extraction (Phase 38 Plans 3-4) writes
    the same envelope shape for freshly-extracted names.

Backfill (T-38-04 tampering mitigation — exact snapshots, round-trip gate,
deterministic ordering, abort-on-blank invariant):

  - Only rows with NO existing structured name part at all (first_name,
    middle_name, last_name, name_suffix all NULL) are examined — a row that
    already carries any operator/import-authored part is left completely
    untouched (never split, never flagged).
  - `full_name` itself is NEVER written by this migration — it was already
    correct pre-upgrade, so it is trivially preserved byte-for-byte for
    every row, confident or ambiguous (D-04/D-10/D-11).
  - Each examined row is split via the pure, deterministic
    api.domain.person_names.split_legacy_full_name (Plan 01, D-10-D-12).
    A High-confidence, round-trip-exact split is applied to the four
    structured columns and name_needs_review is left false. Every other
    shape (particle, single-part, >3 tokens, punctuation/order ambiguity,
    whitespace near-miss) is preserved unapplied and name_needs_review is
    set true (D-11/D-12) — this module never guesses.
  - A blank/whitespace-only full_name violates the migration's own
    precondition and aborts (raises) rather than silently skipping or
    guessing — Postgres transactional DDL rolls the entire migration back
    (schema and data) on any such abort, per the same discipline already
    relied on by migrations 0008/0012's enum-expansion transaction boundary.
  - Deterministic applied/reviewed counts are printed for operator/CI
    visibility (T-38-05 repudiation mitigation).

Downgrade drops only this migration's own two columns, in the reverse
order they were added — it never rewrites full_name or the pre-existing
structured columns (first_name/middle_name/last_name/name_suffix stay
exactly as they ended up after upgrade's backfill).
"""

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from api.domain.person_names import format_full_name, split_legacy_full_name

# revision identifiers, used by Alembic.
revision: str = "0022"
down_revision: Union[str, None] = "0021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns first (Task 2 ordering constraint) so the backfill loop
    # below can write into them.
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

    bind = op.get_bind()

    # Deterministic ordering (T-38-04) — process rows in a stable, repeatable
    # sequence rather than whatever order the database happens to return.
    rows = bind.execute(
        sa.text(
            "SELECT id, full_name, first_name, middle_name, last_name, name_suffix "
            "FROM people ORDER BY id"
        )
    ).fetchall()

    applied_count = 0
    reviewed_count = 0

    for row in rows:
        # Never touch a row that already carries any operator/import-
        # authored structured name part — only truly unconverted legacy
        # full-name-only rows are examined.
        if row.first_name or row.middle_name or row.last_name or row.name_suffix:
            continue

        pre_full_name = row.full_name
        if pre_full_name is None or not pre_full_name.strip():
            raise RuntimeError(
                f"people.id={row.id} has a blank/NULL full_name — cannot "
                "safely backfill (pre-upgrade invariant violated); aborting "
                "migration 0022 rather than guessing or silently skipping."
            )

        stripped_full_name = pre_full_name.strip()
        result = split_legacy_full_name(pre_full_name)

        metadata = {
            "source": "legacy_migration_0022",
            "raw": pre_full_name,
            "confidence": result.confidence,
            "reason": result.reason,
            "auto_applied": result.auto_apply,
        }

        if result.auto_apply:
            # Round-trip gate (T-38-04): re-derive full_name from the split
            # parts and abort the whole migration rather than silently
            # persist any split that does not reproduce the original text
            # exactly.
            recomputed = format_full_name(
                result.first_name,
                result.middle_name,
                result.last_name,
                result.name_suffix,
            )
            if recomputed != stripped_full_name:
                raise RuntimeError(
                    f"people.id={row.id}: split round-trip mismatch "
                    f"({recomputed!r} != {stripped_full_name!r}) — aborting "
                    "migration 0022 rather than persist a lossy split."
                )
            update_result = bind.execute(
                sa.text(
                    "UPDATE people SET "
                    "first_name = :first_name, "
                    "middle_name = :middle_name, "
                    "last_name = :last_name, "
                    "name_suffix = :name_suffix, "
                    "name_needs_review = false, "
                    "name_extraction_metadata = CAST(:metadata AS JSONB) "
                    "WHERE id = :id AND full_name = :expected_full_name"
                ),
                {
                    "first_name": result.first_name,
                    "middle_name": result.middle_name,
                    "last_name": result.last_name,
                    "name_suffix": result.name_suffix,
                    "metadata": json.dumps(metadata),
                    "id": row.id,
                    "expected_full_name": pre_full_name,
                },
            )
            applied_count += 1
        else:
            update_result = bind.execute(
                sa.text(
                    "UPDATE people SET "
                    "name_needs_review = true, "
                    "name_extraction_metadata = CAST(:metadata AS JSONB) "
                    "WHERE id = :id AND full_name = :expected_full_name"
                ),
                {
                    "metadata": json.dumps(metadata),
                    "id": row.id,
                    "expected_full_name": pre_full_name,
                },
            )
            reviewed_count += 1

        if update_result.rowcount != 1:
            raise RuntimeError(
                f"people.id={row.id}: expected exactly one row updated, got "
                f"{update_result.rowcount} — full_name drifted since this "
                "migration's own pre-upgrade snapshot; aborting."
            )

    print(
        f"[0022] backfill complete: {applied_count} applied, "
        f"{reviewed_count} flagged for review"
    )


def downgrade() -> None:
    # Reverse order of upgrade's op.add_column calls. Never rewrites
    # full_name or the pre-existing structured columns — only this
    # migration's own two columns are dropped.
    op.drop_column("people", "name_extraction_metadata")
    op.drop_column("people", "name_needs_review")
