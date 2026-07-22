"""
Pure, dependency-light domain contract for person-name authority (Phase 38).

Covers D-01, D-03, D-05-D-11, D-18, D-22 from
.planning/phases/38-full-name-vs-name-parts-rethink/38-CONTEXT.md:

  - normalize_name_part / format_full_name / prepare_person_name:
    whitespace normalization, canonical `First Middle Last, Suffix`
    formatting, and the first-or-last minimum-data invariant.
  - prepare_name_provenance: validation for the `{value, raw, confidence}`
    extraction-provenance envelope (D-18/D-22).
  - split_legacy_full_name: a conservative, fixture-driven legacy Full Name
    splitter that only ever auto-applies a structurally unambiguous,
    round-trip-exact split (D-10-D-12).

This module has NO FastAPI/SQLAlchemy/Alembic imports. It must remain
importable by API services, pipeline commands, tests, and Alembic
migrations without initializing the app or a database connection
(T-38-01/T-38-02 — bounded, deterministic, linear-time processing only).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Optional

# ---------------------------------------------------------------------------
# Column bounds (api/models/models.py Person columns) — deterministic domain
# validation errors, never silent truncation.
# ---------------------------------------------------------------------------

FIRST_NAME_MAX_LENGTH = 150
MIDDLE_NAME_MAX_LENGTH = 150
LAST_NAME_MAX_LENGTH = 150
NAME_SUFFIX_MAX_LENGTH = 50
FULL_NAME_MAX_LENGTH = 300

_PART_BOUNDS = {
    "first_name": FIRST_NAME_MAX_LENGTH,
    "middle_name": MIDDLE_NAME_MAX_LENGTH,
    "last_name": LAST_NAME_MAX_LENGTH,
    "name_suffix": NAME_SUFFIX_MAX_LENGTH,
}

# Provenance envelope bounds (T-38-01) — value mirrors a single name part;
# raw mirrors the full extracted-source-text bound used by full_name.
PROVENANCE_VALUE_MAX_LENGTH = 150
PROVENANCE_RAW_MAX_LENGTH = 300

_WHITESPACE_RE = re.compile(r"\s+")

ConfidenceBand = Literal["High", "Medium", "Low"]
_CONFIDENCE_CANONICAL = {"high": "High", "medium": "Medium", "low": "Low"}


class PersonNameError(ValueError):
    """
    Deterministic validation error raised by this module.

    `code` is a stable machine-readable identifier (e.g. "length_exceeded")
    for callers/tests to branch on without depending on message wording.
    """

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


# ---------------------------------------------------------------------------
# Normalization / canonical formatting (D-05-D-09)
# ---------------------------------------------------------------------------


def normalize_name_part(raw: Optional[str], *, field_name: str) -> Optional[str]:
    """
    Trim and collapse internal whitespace; map blank to None.

    Never changes capitalization or punctuation (D-06/D-07) — initials,
    hyphens, apostrophes, particles, compound values, and suffix spelling
    are preserved exactly as authored. Raises PersonNameError (never
    truncates) when the normalized value exceeds the column bound for
    `field_name`.
    """
    if raw is None:
        return None
    collapsed = _WHITESPACE_RE.sub(" ", raw.strip())
    if not collapsed:
        return None
    bound = _PART_BOUNDS.get(field_name)
    if bound is not None and len(collapsed) > bound:
        raise PersonNameError(
            "length_exceeded",
            f"{field_name} exceeds maximum length of {bound} characters "
            f"(got {len(collapsed)})",
        )
    return collapsed


def format_full_name(
    first: Optional[str],
    middle: Optional[str],
    last: Optional[str],
    suffix: Optional[str],
) -> str:
    """
    Canonical `First Middle Last, Suffix` formatter (D-05).

    Blank Middle/Suffix are omitted without leaving extra spaces or
    punctuation. Callers are expected to have already normalized each part
    via normalize_name_part — this function does not re-trim or reject
    per-part length, only the derived full_name's own compatibility bound.
    """
    name_parts = [p for p in (first, middle, last) if p]
    full_name = " ".join(name_parts)
    if suffix:
        full_name = f"{full_name}, {suffix}" if full_name else suffix

    if len(full_name) > FULL_NAME_MAX_LENGTH:
        raise PersonNameError(
            "full_name_length_exceeded",
            f"full_name exceeds maximum length of {FULL_NAME_MAX_LENGTH} "
            f"characters (got {len(full_name)})",
        )
    return full_name


@dataclass(frozen=True)
class PreparedPersonName:
    first_name: Optional[str]
    middle_name: Optional[str]
    last_name: Optional[str]
    name_suffix: Optional[str]
    full_name: str


def prepare_person_name(
    first: Optional[str] = None,
    middle: Optional[str] = None,
    last: Optional[str] = None,
    suffix: Optional[str] = None,
) -> PreparedPersonName:
    """
    Normalize authored name parts and derive the canonical full_name.

    One shared derivation rule for every create/update write path (D-01/D-03):
    normalize each part, require at least first or last (D-09), then derive
    full_name from the normalized parts. Raises PersonNameError when both
    first and last are blank after normalization.
    """
    norm_first = normalize_name_part(first, field_name="first_name")
    norm_middle = normalize_name_part(middle, field_name="middle_name")
    norm_last = normalize_name_part(last, field_name="last_name")
    norm_suffix = normalize_name_part(suffix, field_name="name_suffix")

    if not norm_first and not norm_last:
        raise PersonNameError(
            "at_least_one_required",
            "At least first_name or last_name is required",
        )

    full_name = format_full_name(norm_first, norm_middle, norm_last, norm_suffix)

    return PreparedPersonName(
        first_name=norm_first,
        middle_name=norm_middle,
        last_name=norm_last,
        name_suffix=norm_suffix,
        full_name=full_name,
    )


# ---------------------------------------------------------------------------
# Provenance envelope (D-18/D-22, T-38-01)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NameProvenance:
    value: Optional[str]
    raw: Optional[str]
    confidence: ConfidenceBand


def prepare_name_provenance(
    value: Optional[str], raw: Optional[str], confidence: str
) -> NameProvenance:
    """
    Validate a single extracted-field provenance envelope (D-18, T-38-01).

    Accepts only value/raw strings within bounds and a qualitative
    High/Medium/Low confidence label (D-22, case-insensitive input,
    normalized to canonical Title-case output). Raises PersonNameError for
    malformed/oversized envelopes. Raw text is preserved exactly apart from
    the length bound — never re-trimmed or rewritten — so the operator sees
    the exact extracted source text (D-18).
    """
    confidence_key = (confidence or "").strip().lower()
    if confidence_key not in _CONFIDENCE_CANONICAL:
        raise PersonNameError(
            "invalid_confidence",
            f"confidence must be one of {sorted(_CONFIDENCE_CANONICAL.values())}, "
            f"got {confidence!r}",
        )

    if value is not None and len(value) > PROVENANCE_VALUE_MAX_LENGTH:
        raise PersonNameError(
            "provenance_value_length_exceeded",
            f"provenance value exceeds maximum length of "
            f"{PROVENANCE_VALUE_MAX_LENGTH} characters (got {len(value)})",
        )

    if raw is not None and len(raw) > PROVENANCE_RAW_MAX_LENGTH:
        raise PersonNameError(
            "provenance_raw_length_exceeded",
            f"provenance raw exceeds maximum length of "
            f"{PROVENANCE_RAW_MAX_LENGTH} characters (got {len(raw)})",
        )

    return NameProvenance(
        value=value, raw=raw, confidence=_CONFIDENCE_CANONICAL[confidence_key]
    )
