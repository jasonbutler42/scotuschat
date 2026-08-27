"""
Curated-vocabulary stage-direction detection.

D-17 requires matching against a curated vocabulary inside EITHER
brackets or parens, typo-tolerantly -- never a blind "anything inside
brackets/parens" capture. A direct scan of utterances.jsonl found parens
heavily overloaded with legitimate non-stage-direction content
(legal-list markers like ``(a)``/``(b)``/``(1)``/``(2)`` and the ``(ph)``
"phonetic spelling, name uncertain" transcript convention) that a blind
paren regex would misclassify.

``detect_stage_direction`` returns the normalized canonical marker label
(e.g. ``"Laughter"``) when the given text IS a stage direction (the whole
turn's text is the marker), else ``None``.
"""

from __future__ import annotations

import difflib
import re

# Normalized marker text -> canonical display label. Multiple normalized
# variants (e.g. "laugh"/"laughs"/"laughter") map to the same canonical
# label since they're the same real-world event.
_CANONICAL_LABELS: dict[str, str] = {
    "inaudible": "Inaudible",
    "laughter": "Laughter",
    "laughs": "Laughter",
    "laugh": "Laughter",
    "voice overlap": "Voice Overlap",
    "recess": "Recess",
    "luncheon recess": "Luncheon Recess",
    "cross talk": "Cross Talk",
}

# Public curated-vocabulary collection (base terms), exposed for callers
# that need to introspect what markers are recognized.
CURATED_MARKERS = frozenset(_CANONICAL_LABELS.values())

# Tokens that must NEVER be classified as stage directions even though
# they appear alone inside brackets/parens -- these are real transcript
# conventions, not stage directions (the explicit anti-case for D-17).
_REJECTED_LITERALS = frozenset({"a", "b", "c", "d", "ph"})

# Matches text that is ENTIRELY a single bracketed-or-parenthesized token
# (whole-turn marker text, per D-16/D-17) -- not a parenthetical embedded
# inside a longer sentence.
_WHOLE_TURN_MARKER_RE = re.compile(r"^\s*[\[\(]([^\[\]\(\)]*)[\]\)]\s*$")

_FUZZY_CUTOFF = 0.8


def _normalize(token: str) -> str:
    token = token.lower().strip()
    token = re.sub(r"[^\w\s]", "", token)
    token = re.sub(r"\s+", " ", token).strip()
    return token


def detect_stage_direction(text: str | None) -> str | None:
    """
    Return the canonical stage-direction label for ``text`` if the whole
    text is a curated-vocabulary marker inside brackets or parens, else
    ``None``.
    """
    if not text:
        return None

    match = _WHOLE_TURN_MARKER_RE.match(text)
    if not match:
        return None

    inner = _normalize(match.group(1))
    if not inner:
        return None

    # Reject numeric-only tokens (legal-list markers like "1"/"2") and the
    # curated set of single-letter/phonetic literals (a/b/ph) before ever
    # attempting a fuzzy match.
    if inner.isdigit() or inner in _REJECTED_LITERALS:
        return None

    if inner in _CANONICAL_LABELS:
        return _CANONICAL_LABELS[inner]

    close_matches = difflib.get_close_matches(
        inner, _CANONICAL_LABELS.keys(), n=1, cutoff=_FUZZY_CUTOFF
    )
    if close_matches:
        return _CANONICAL_LABELS[close_matches[0]]

    return None
