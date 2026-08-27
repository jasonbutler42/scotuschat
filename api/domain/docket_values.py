"""
Pure, dependency-light domain contract for docket-value authority (Phase 38,
gap closure G-38-6 / T-38-20, T-38-21, T-38-25).

Closes an authenticated-admin arbitrary-file-write primitive: `primary_docket`
and `source_dockets` (operator-supplied docket "numbers" submitted on the
Pipeline Runner new-job form) had no character allow-list and no length cap
anywhere between the browser and
`Path("data/pdfs") / f"{primary_docket}-q{n}.pdf"` in
`pipeline/commands/ingest.py`. A value containing a path separator, a `..`
traversal segment, a POSIX-absolute or Windows-drive-letter prefix, or simply
exceeding a sane length could crash ingest ([Errno 22]) or — worse — cause
the write to land outside `data/pdfs/` entirely (pathlib's `/` operator
honors `../` segments and silently discards the left operand when the right
operand is an absolute path). See .planning/debug/docket-filename-injection.md
for the full diagnosis.

This module has NO FastAPI/SQLAlchemy/Alembic imports. It must remain
importable by API services, pipeline commands, and tests without
initializing the app or a database connection — mirroring
api/domain/person_names.py's structural conventions exactly.

Why a character allow-list rather than a strict SCOTUS docket-shape regex
(e.g. the cover extractor's `\\d{1,2}-\\d+`): post-ingest editing already
accepts any non-blank docket string (`ArgumentUpdate.docket_number`,
`MetadataUpdate.source_docket`), the ConvoKit historical importer
legitimately writes shapes like `71` and `1955-71`, ingest itself generates
synthetic `job-{id}` dockets, and `data/pdfs/` already holds operator-created
files such as `bananas-q1.pdf` and `0-9999-q1.pdf`. A strict shape regex
would reject values the rest of the system accepts and already stores; the
character allow-list plus length cap closes the entire path-hazard class (no
separator, no dot, no quote, no whitespace, no control character can match)
without contradicting any existing accepted shape.
"""

from __future__ import annotations

import re
from typing import Optional

# ---------------------------------------------------------------------------
# Rule constants (T-38-25: the single canonical copy of this rule)
# ---------------------------------------------------------------------------

# Accepted-length cap. Real docket shapes ("22-915", "job-1120",
# "14-556-TEST-SEED") are all well under this; it exists to bound the
# arbitrary-file-write / DoS surface, not to model any real docket
# format.
DOCKET_VALUE_MAX_LENGTH = 64

# Kept as a plain string literal (not only a compiled pattern object) because
# Phase 38 Plan 09's TypeScript mirror must declare the byte-identical
# literal, and a contract test asserts the two literals are equal.
#
# Leading character must be alphanumeric (independently subsumes the T-24-08
# argv-flag-injection class: "-1" and "--dockets" cannot match), followed by
# any run of alphanumeric/underscore/hyphen characters. No separator, no
# dot, no quote, no whitespace, and no control character can ever match.
DOCKET_VALUE_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_-]*$"

_DOCKET_VALUE_RE = re.compile(DOCKET_VALUE_PATTERN)

# Bounded-echo budget for error messages (mirrors the T-24-10 bounded-message
# precedent in pipeline/__main__.py::_write_early_failure) — a
# multi-kilobyte submitted value must never inflate a 422 body or an
# admin_jobs.error_message column.
DOCKET_VALUE_ECHO_LIMIT = 32

_ELLIPSIS = "…"


class DocketValueError(ValueError):
    """
    Deterministic validation error raised by this module.

    `code` is a stable machine-readable identifier (one of "empty",
    "length_exceeded", "invalid_characters") for callers/tests to branch on
    without depending on message wording.
    """

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _bounded_echo(value: str) -> str:
    """Bound an echoed value to DOCKET_VALUE_ECHO_LIMIT characters plus an
    ellipsis when truncated, so a caller cannot inflate a 422 body or the
    admin_jobs.error_message column via an oversized docket value."""
    if len(value) <= DOCKET_VALUE_ECHO_LIMIT:
        return value
    return value[:DOCKET_VALUE_ECHO_LIMIT] + _ELLIPSIS


def normalize_docket_value(raw: Optional[str]) -> str:
    """
    Validate and normalize a single operator-supplied docket value.

    Ordering is a hard determinism contract: blank check, then length
    check, then pattern check. (This ordering matters for cases like the
    reported UAT string, which is both over-length and pattern-invalid —
    its raised code is deterministically "length_exceeded" because the
    length check runs first.)

    Raises DocketValueError with code:
      - "empty" when the stripped value is blank (or raw is None)
      - "length_exceeded" when it exceeds DOCKET_VALUE_MAX_LENGTH
      - "invalid_characters" when it does not match DOCKET_VALUE_PATTERN

    Returns the stripped value unchanged otherwise. Uses re.fullmatch (not
    match) so a trailing newline cannot slip past the anchors — this is
    also what keeps Python and JavaScript verdicts identical for the same
    literal.
    """
    value = (raw or "").strip()

    if not value:
        raise DocketValueError("empty", "Docket value cannot be blank.")

    if len(value) > DOCKET_VALUE_MAX_LENGTH:
        raise DocketValueError(
            "length_exceeded",
            f"Docket value {_bounded_echo(value)!r} exceeds maximum length "
            f"of {DOCKET_VALUE_MAX_LENGTH} characters (got {len(value)}).",
        )

    if not _DOCKET_VALUE_RE.fullmatch(value):
        raise DocketValueError(
            "invalid_characters",
            f"Docket value {_bounded_echo(value)!r} contains characters "
            "that are not allowed. Only letters, numbers, underscores, and "
            "hyphens are permitted, and the value must start with a letter "
            "or number.",
        )

    return value
