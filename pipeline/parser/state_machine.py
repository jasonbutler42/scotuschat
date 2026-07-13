"""
Rule-based SCOTUS oral argument transcript parser.

Adapted from spike:
  .claude/skills/spike-findings-scotuschat/sources/002-parse-prompt-schema/parse.py

Two mandatory fixes applied over the spike source:

1. F04 fix — ON\\s+BEHALF\\s+OF added to TOC_SECTION_RE.
   Without this, "ON BEHALF OF PETITIONERS ON QUESTION 1" in Obergefell gets
   appended to the prior speaker's utterance text.

2. Section hint cascade fix — Two-variable design:
   - pending_section_hint: set when TOC_SECTION_RE matches
   - current_section_hint: consumed from pending_section_hint at each new
     speaker turn start, then cleared to None
   Prevents ALL utterances after a section marker from inheriting section_hint.

No LLM calls in this module — rule-based only.
"""

import re
from typing import Optional


# ---------------------------------------------------------------------------
# Regex constants — copied from spike with F04 fix applied
# ---------------------------------------------------------------------------

# Legal transcript line numbers: "1 " … "25 " at column 0
LINE_NUM_RE = re.compile(r"^\s{0,3}(\d{1,2})\s")

# Header/footer lines to skip entirely
HEADER_RE = re.compile(
    r"^(?:Official|ALDERSON|Heritage|HERITAGE|Alderson|www\.|http|\(202\)|\d{3,4}\s+L\s+Street)",
    re.IGNORECASE,
)

# Pure page-number lines (just digits, nothing else)
PAGE_NUM_RE = re.compile(r"^\d+$")

# Table-of-contents / section-marker lines — not utterances, but signal section transitions.
# F04 fix: ON\s+BEHALF\s+OF added to handle "ON BEHALF OF PETITIONERS ON QUESTION 1"
# variant present in Obergefell. Without this, it is appended to the prior speaker.
TOC_SECTION_RE = re.compile(
    r"^(?:ORAL\s+ARGUMENT\s+OF|REBUTTAL\s+ARGUMENT\s+(?:OF)?|REBUTTAL\s+ARGUMENT\s*:?"
    r"|ON\s+BEHALF\s+OF)"
    r"(?:\s+.*)?$",
    re.IGNORECASE,
)

# Speaker label: ALL-CAPS prefix followed by colon.
# Handles: JUSTICE X, CHIEF JUSTICE X, MR. X, MS. X, GENERAL X, and bare
# ALL-CAPS names (e.g. "QUESTION:" used in some older transcripts).
SPEAKER_RE = re.compile(
    r"^("
    r"CHIEF\s+JUSTICE(?:\s+[A-Z][A-Z\s'.\-]+?)?"
    r"|JUSTICE\s+[A-Z][A-Z\s'.\-]+"
    r"|MR\.\s+[A-Z][A-Z\s'.\-]+"
    r"|MS\.\s+[A-Z][A-Z\s'.\-]+"
    r"|MRS\.\s+[A-Z][A-Z\s'.\-]+"
    r"|GENERAL\s+[A-Z][A-Z\s'.\-]+"
    r"|QUESTION"
    r")"
    r":\s*(.*)",
    re.DOTALL,
)

# Standalone stage direction: entire line is "(text)" or ends with a closing paren
STAGE_DIR_RE = re.compile(r"^\(([^)]+)\)\.?\s*$")

# Stage direction that terminates a sentence: "...text. (Whereupon, ...)"
# Captured so we can split the sentence from the direction.
TERMINAL_STAGE_RE = re.compile(r"^(.*?)\s*(\([^)]{4,}\)\.?)\s*$", re.DOTALL)

# Word-index page detector
WORD_INDEX_RE = re.compile(r"^\w[\w\s,'.\-]{0,30}\s+\[\d+\]\s+\d+:\d+")

# Inline stage direction within a line: "(text)" surrounded by other content
INLINE_STAGE_RE = re.compile(r"\(([^)]{2,60})\)")

# Section hint mapping from TOC marker text → canonical value.
# RESPONDENT/PETITIONER use an optional trailing "S" — real transcripts almost
# always use the plural ("ON BEHALF OF PETITIONERS", e.g. Obergefell) since a
# consolidated case can have multiple counsel on a side. \bPETITIONER\b alone
# never matches "PETITIONERS" (the trailing S removes the word boundary right
# after "PETITIONER"), which silently dropped every section_hint on plural TOC
# markers — surfaced by pipeline/tests/test_parse.py::test_section_hint_not_cascade.
SECTION_HINT_MAP = [
    (re.compile(r"\bREBUTTAL\b",       re.IGNORECASE), "rebuttal"),
    (re.compile(r"\bAMICUS\b",         re.IGNORECASE), "amicus"),
    (re.compile(r"\bRESPONDENTS?\b",   re.IGNORECASE), "respondent"),
    (re.compile(r"\bPETITIONERS?\b",   re.IGNORECASE), "petitioner"),
    (re.compile(r"\bUNITED STATES\b",  re.IGNORECASE), "amicus"),
]

# Lines that look like case captions (false-positive speaker labels)
CAPTION_SKIP_RE = re.compile(r"^(?:ET AL\.|APPEARANCES|PETITIONERS?|RESPONDENTS?)$")


# ---------------------------------------------------------------------------
# Side assignment — deterministic, rule-based (D-09 / Open Question #3 resolution)
# ---------------------------------------------------------------------------

BENCH_RE = re.compile(r"^(?:CHIEF\s+JUSTICE|JUSTICE\s+|QUESTION)", re.IGNORECASE)
ADVOCATE_RE = re.compile(r"^(?:MR\.|MS\.|MRS\.|GENERAL\s+)", re.IGNORECASE)


def assign_side(raw_speaker_label: Optional[str], is_stage_direction: bool) -> str:
    """
    Assign side deterministically from raw speaker label.

    Returns one of: "BENCH", "ADVOCATE", "UNKNOWN"

    Stage directions and unrecognized labels return "UNKNOWN".
    This matches SideEnum values in api/models/models.py.
    """
    if is_stage_direction or raw_speaker_label is None:
        return "UNKNOWN"
    if BENCH_RE.match(raw_speaker_label):
        return "BENCH"
    if ADVOCATE_RE.match(raw_speaker_label):
        return "ADVOCATE"
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_section_hint(toc_text: str) -> Optional[str]:
    """Map TOC section marker text to a canonical section hint string."""
    for pattern, hint in SECTION_HINT_MAP:
        if pattern.search(toc_text):
            return hint
    return None


def _split_inline_stages(text: str) -> list[tuple[str, bool]]:
    """
    Split a text string on inline stage directions.

    Returns list of (segment_text, is_stage_direction).
    E.g. "So I think -- (Laughter.) -- the point is"
      → [("So I think --", False), ("(Laughter.)", True), ("-- the point is", False)]

    Only splits on patterns that look like genuine stage directions, not
    legal citations (page:line references like "12:5" are skipped).
    """
    segments = []
    last = 0
    for m in INLINE_STAGE_RE.finditer(text):
        # Heuristic: genuine stage directions are short; skip page:line refs
        content = m.group(1)
        if re.search(r"\d{1,3}:\d{1,2}", content):   # "12:5" — page:line ref, skip
            continue
        before = text[last:m.start()].strip()
        if before:
            segments.append((before, False))
        segments.append((m.group(0), True))
        last = m.end()
    tail = text[last:].strip()
    if tail:
        segments.append((tail, False))
    return segments if len(segments) > 1 else [(text, False)]


# ---------------------------------------------------------------------------
# State machine parser
# ---------------------------------------------------------------------------


def parse_transcript(pages: list[str]) -> list[dict]:
    """
    Parse cleaned transcript pages into a list of utterance dicts.

    Args:
        pages: List of cleaned page text strings from extract_pages().

    Returns:
        List of dicts with keys:
            sequence (int): 1-based, global across the full argument
            raw_speaker_label (Optional[str]): None for stage directions
            text (str): full utterance text, continuation lines merged with space
            is_stage_direction (bool): True for (Laughter.), (Brief pause.), etc.
            section_hint (Optional[str]): 'petitioner'|'respondent'|'rebuttal'|'amicus'
                — set only on the FIRST utterance after each section transition
            side (str): 'BENCH'|'ADVOCATE'|'UNKNOWN'

    Section hint cascade fix (Pitfall 3):
        Two separate variables are used:
        - pending_section_hint: set when TOC marker is detected
        - current_section_hint: consumed from pending_section_hint at each new
          speaker turn start, then cleared to None after flush
        This prevents the hint from cascading to all utterances after the marker.
    """
    utterances: list[dict] = []
    seq = 0

    # Section hint cascade fix — two variables, not one:
    # pending_section_hint: set when a TOC marker is seen;
    #   consumed by the NEXT speaker flush.
    pending_section_hint: Optional[str] = None
    # current_section_hint: hint that belongs to the utterance currently being built.
    #   Cleared after flush so it does NOT cascade to subsequent utterances.
    current_section_hint: Optional[str] = None

    current_speaker: Optional[str] = None
    current_text_parts: list[str] = []

    def flush():
        nonlocal current_speaker, current_text_parts, seq, current_section_hint
        if not current_text_parts and current_speaker is None:
            return
        raw_text = " ".join(p for p in current_text_parts if p)
        if not raw_text.strip():
            current_speaker = None
            current_text_parts = []
            current_section_hint = None
            return

        # Check for a terminal stage direction embedded at the end of the text
        # e.g. "The case is submitted. (Whereupon, at 11:54 a.m., the case was submitted.)"
        tm = TERMINAL_STAGE_RE.match(raw_text.strip())
        if tm and tm.group(1).strip() and STAGE_DIR_RE.match(tm.group(2)):
            # Emit the spoken part first
            seq += 1
            utterances.append({
                "sequence": seq,
                "raw_speaker_label": current_speaker,
                "text": tm.group(1).strip(),
                "is_stage_direction": False,
                "section_hint": current_section_hint,
                "side": assign_side(current_speaker, False),
            })
            current_section_hint = None
            # Then emit the stage direction
            seq += 1
            utterances.append({
                "sequence": seq,
                "raw_speaker_label": None,
                "text": tm.group(2).strip(),
                "is_stage_direction": True,
                "section_hint": None,
                "side": assign_side(None, True),
            })
        else:
            seq += 1
            utterances.append({
                "sequence": seq,
                "raw_speaker_label": current_speaker,
                "text": raw_text.strip(),
                "is_stage_direction": False,
                "section_hint": current_section_hint,
                "side": assign_side(current_speaker, False),
            })
            current_section_hint = None

        current_speaker = None
        current_text_parts = []

    def emit_stage(text: str):
        nonlocal seq
        seq += 1
        utterances.append({
            "sequence": seq,
            "raw_speaker_label": None,
            "text": text,
            "is_stage_direction": True,
            "section_hint": None,
            "side": assign_side(None, True),
        })

    for page_text in pages:
        for line in page_text.split("\n"):
            line = line.strip()
            if not line:
                continue

            # ── Table-of-contents / section markers ──────────────────────────
            # Set pending_section_hint — NOT current_section_hint.
            # It will be consumed at the next speaker turn start (cascade fix).
            if TOC_SECTION_RE.match(line):
                pending_section_hint = _resolve_section_hint(line)
                continue

            # ── Standalone stage direction ────────────────────────────────────
            if STAGE_DIR_RE.match(line):
                flush()
                emit_stage(line)
                continue

            # ── Speaker turn ──────────────────────────────────────────────────
            m = SPEAKER_RE.match(line)
            if m:
                label = m.group(1).strip().rstrip(":")
                if CAPTION_SKIP_RE.match(label):
                    continue
                rest = m.group(2).strip()

                # Flush previous speaker (their hint is already stored in current_section_hint)
                flush()

                # Cascade fix: consume the pending hint for THIS new speaker only,
                # then immediately clear pending_section_hint.
                current_section_hint = pending_section_hint
                pending_section_hint = None

                # Check if rest has inline stage directions
                if rest and INLINE_STAGE_RE.search(rest):
                    segments = _split_inline_stages(rest)
                    first = True
                    for seg_text, is_stage in segments:
                        if not seg_text.strip():
                            continue
                        if is_stage:
                            emit_stage(seg_text)
                        else:
                            seq += 1
                            utterances.append({
                                "sequence": seq,
                                "raw_speaker_label": label,
                                "text": seg_text.strip(),
                                "is_stage_direction": False,
                                "section_hint": current_section_hint if first else None,
                                "side": assign_side(label, False),
                            })
                            first = False
                    current_section_hint = None
                    current_speaker = label
                    current_text_parts = []
                elif rest:
                    current_speaker = label
                    current_text_parts = [rest]
                    # current_section_hint already set above; will be used at flush()
                else:
                    current_speaker = label
                    current_text_parts = []
                continue

            # ── Continuation line ─────────────────────────────────────────────
            if current_speaker is not None:
                if INLINE_STAGE_RE.search(line):
                    segments = _split_inline_stages(line)
                    if len(segments) > 1:
                        if current_text_parts:
                            current_text_parts.append(segments[0][0])
                        flush()
                        for seg_text, is_stage in segments[1:]:
                            if not seg_text.strip():
                                continue
                            if is_stage:
                                emit_stage(seg_text)
                            else:
                                current_speaker = (
                                    utterances[-1]["raw_speaker_label"]
                                    if utterances else current_speaker
                                )
                                current_text_parts = [seg_text]
                        continue
                current_text_parts.append(line)

    flush()
    return utterances
