"""
Pure, dependency-light domain contract for `Argument.slug` generation
(Phase 51, plan 51-02, D-12/D-13).

This module has NO FastAPI/SQLAlchemy/Alembic imports. It must remain
importable by API services, pipeline commands, and tests without
initializing the app or a database connection — mirroring
api/domain/content_digest.py's and api/domain/authority.py's structural
conventions exactly.

`derive_argument_slug` reuses `pipeline.commands.ingest._derive_slug` as
its base case-name-to-slug transform rather than forking a second
implementation — that import direction (api -> pipeline for this one
helper) is already established by api/services/admin_arguments.py.

Suffix discriminator choice (Claude's Discretion, CONTEXT.md): queried the
real ~7,800-row ConvoKit corpus (data/corpus/cases.jsonl) before writing
this function. 952 of 7,748 cases (~12%) carry more than one transcript
(the population that ever needs a suffix, since two arguments sharing one
case_name share one base slug). Within those 952 cases, simulating the
importer's own `_parse_argued_date` found 434 (45.6%) where two
transcripts resolve to the SAME argued_date or to no date at all — nearly
half. `question_number`, by contrast, is a purely synthetic counter
(`_next_question_number`, max+1 per docket) assigned by the importer
itself at write time: always populated, always unique-by-construction,
never derived from parseable corpus text. `question_number` is therefore
the primary discriminator; `argued_date` is a secondary fallback for the
(mostly PDF-path) case where `question_number` is itself absent; a plain
incrementing counter is the last-resort fallback that always terminates.
"""

from __future__ import annotations

import datetime

from pipeline.commands.ingest import _derive_slug

# D-13: `/arguments/term/{year}` (plan 51-08) coexists with `/arguments/{slug}`.
# A minted slug must never shadow the literal path segment "term".
RESERVED_SLUG_WORDS: frozenset[str] = frozenset({"term"})

# Fallback base slug when a case name derives to an empty string (e.g. a
# name composed entirely of characters _derive_slug strips) — never return
# an empty string from this function.
_EMPTY_BASE_FALLBACK = "argument"


def derive_argument_slug(
    case_name: str,
    *,
    question_number: int | None = None,
    argued_date: datetime.date | None = None,
    taken: set[str] | None = None,
) -> str:
    """
    Derive a unique, URL-safe, non-reserved slug for one Argument row.

    - The bare base slug (from `case_name`) is returned when it is neither
      reserved (D-13) nor already `taken`.
    - Otherwise a deterministic suffix is appended: `question_number`
      first (always populated and unique-by-construction for the corpus
      import path), then `argued_date` (ISO date), then a plain
      incrementing integer — the last of which always terminates because
      it is checked against `taken` on every attempt.
    - Never returns a member of `RESERVED_SLUG_WORDS`.
    - Never returns an empty string.

    `taken` is the caller-supplied set of slugs already in use (e.g. from
    a `SELECT Argument.slug` scoped to this base) — this function does not
    touch the database. The database's `uq_arguments_slug` unique
    constraint remains the backstop against a race this in-memory check
    cannot see.
    """
    taken = taken or set()

    base = _derive_slug(case_name)
    if not base:
        base = _EMPTY_BASE_FALLBACK

    def _available(candidate: str) -> bool:
        return candidate not in RESERVED_SLUG_WORDS and candidate not in taken

    if _available(base):
        return base

    if question_number is not None:
        candidate = f"{base}-q{question_number}"
        if _available(candidate):
            return candidate

    if argued_date is not None:
        candidate = f"{base}-{argued_date.isoformat()}"
        if _available(candidate):
            return candidate

    # Last-resort fallback: a plain incrementing counter. Guaranteed to
    # terminate — `taken` is a finite set and each iteration tries a
    # candidate no earlier iteration could have produced.
    n = 2
    while True:
        candidate = f"{base}-{n}"
        if _available(candidate):
            return candidate
        n += 1
