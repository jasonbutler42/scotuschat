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

Phase 53 (D-04/D-08/D-09): the curated vocabulary splits into two classes.
``INAUDIBLE_LABEL`` ("Inaudible") is the one transcription failure -- a
whole-turn marker with a known speaker keeps that speaker (it is their
turn, just with the words lost), never a stage direction. Every other
curated label in ``ROOM_EVENT_LABELS`` is a room event -- unattributed,
exactly as before (D-03). ``canonical_marker_text`` is the one place that
wraps a curated label in the D-08 display form; callers never re-implement
that wrapping.
"""

from __future__ import annotations

import difflib
import re

# D-04: the one curated label that is a transcription failure, not a room
# event -- a whole-turn marker with this label keeps its known speaker.
INAUDIBLE_LABEL: str = "Inaudible"

# Normalized marker text -> canonical display label. Multiple normalized
# variants (e.g. "laugh"/"laughs"/"laughter") map to the same canonical
# label since they're the same real-world event.
_CANONICAL_LABELS: dict[str, str] = {
    "inaudible": INAUDIBLE_LABEL,
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

# D-03: every curated label except Inaudible is a room event -- unattributed
# regardless of who "said" it.
ROOM_EVENT_LABELS = frozenset(CURATED_MARKERS - {INAUDIBLE_LABEL})

# Tokens that must NEVER be classified as stage directions even though
# they appear alone inside brackets/parens -- these are real transcript
# conventions, not stage directions (the explicit anti-case for D-17).
_REJECTED_LITERALS = frozenset({"a", "b", "c", "d", "ph"})

# Matches text that is ENTIRELY a single bracketed-or-parenthesized token
# (whole-turn marker text, per D-16/D-17) -- not a parenthetical embedded
# inside a longer sentence. Trailing periods after the closing bracket
# (e.g. "(Inaudible)." / "[Inaudible].") are tolerated (Phase 53 CONTEXT.md
# Claude's Discretion) -- the leading/inner capture is unchanged, so
# _REJECTED_LITERALS and the digit rejection below still guard "(a)."/"(1).".
_WHOLE_TURN_MARKER_RE = re.compile(r"^\s*[\[\(]([^\[\]\(\)]*)[\]\)][.]*\s*$")

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


def canonical_marker_text(label: str) -> str:
    """
    Return the D-08 canonical display form for a curated marker `label` --
    the label wrapped in round parens, e.g. "Voice Overlap" ->
    "(Voice Overlap)". Raises ``ValueError`` for any label not in
    ``CURATED_MARKERS`` so no uncurated string can ever be emitted as a
    marker (defense in depth alongside ``detect_stage_direction`` already
    only ever returning a curated label).
    """
    if label not in CURATED_MARKERS:
        raise ValueError(f"{label!r} is not a curated marker label")
    return f"({label})"
