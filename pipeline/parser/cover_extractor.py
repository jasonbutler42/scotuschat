"""
Cover-page metadata extractor for SCOTUS oral argument transcripts.

Reads pages 0–2 (the cover, case caption, and TOC/appearances pages that
extract_pages skips) and extracts:
  - argued_date: the date the argument was heard
  - case_name: the lead petitioner name from the case caption

Both public functions are fail-safe per D-05 / D-09: any exception returns
an empty dict; the parse step continues normally and leaves existing DB
values unchanged.

Tested transcript range: Obergefell 2015 (Alderson) through Rahimi 2023 (Heritage).
"""

import re
from datetime import date
from pathlib import Path

import pdfplumber

# Reuse three constants from extractor.py — do NOT redefine them here.
from pipeline.parser.extractor import HEADER_RE, PAGE_NUM_RE, strip_line_number

# ---------------------------------------------------------------------------
# Regex constants
# ---------------------------------------------------------------------------

# Date line — matches both Alderson and Heritage inline formats:
#   Alderson: 'Tuesday, April 28, 2015'
#   Heritage inline: 'Wednesday, April 24, 2024'
DATE_LINE_RE = re.compile(
    r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+'
    r'(January|February|March|April|May|June|July|August|September|October|November|December)'
    r'\s+(\d{1,2}),\s+(\d{4})',
    re.IGNORECASE,
)

# Heritage cover-page (page 0, no line numbers) date format:
#   'Date: April 24, 2024'
HERITAGE_DATE_RE = re.compile(
    r'Date:\s+'
    r'(January|February|March|April|May|June|July|August|September|October|November|December)'
    r'\s+(\d{1,2}),\s+(\d{4})',
    re.IGNORECASE,
)

# Case caption separator line — Alderson uses soft hyphens (\xad), Heritage uses dashes
CAPTION_SEP_RE = re.compile(r'^[\xad\-\s–—xX\*]+$')

# Trailing case-caption punctuation to strip from name lines (e.g., ' :' ' )' ' ,')
CAPTION_PUNCT_RE = re.compile(r'\s*[:),]\s*$')

# TOC advocate name line: 'MARY L. BONAUTO, ESQ.' or 'GEN. DONALD B. VERRILLI, JR., ESQ.'
TOC_ESQ_RE = re.compile(
    r'^(?:(?:GEN|MR|MS|MRS|DR)\.\s+)?[A-Z][A-Z\s.,]+,\s*ESQ(?:UIRE)?\.?\s*$',
    re.IGNORECASE,
)

# TOC side attribution line: 'On behalf of the Petitioner 3' / 'On behalf of Respondents...'
TOC_SIDE_RE = re.compile(
    r'[Oo]n behalf of(?:\s+the)?\s+(Petitioner|Respondent|Petitioners|Respondents)',
    re.IGNORECASE,
)

# TOC amicus line: 'For the United States, as amicus curiae' / 'as amicus curiae'
TOC_AMICUS_RE = re.compile(r'amicus\s+curiae', re.IGNORECASE)

# Month name → integer mapping (first 3 lowercase letters)
_MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _clean_lines(raw: str) -> list[str]:
    """
    Split raw page text on newlines, strip transcript line numbers, and drop
    header/footer lines matched by HEADER_RE and bare page-number lines
    matched by PAGE_NUM_RE.
    """
    lines = []
    for raw_line in raw.split("\n"):
        line = strip_line_number(raw_line).strip()
        if line and not HEADER_RE.match(line) and not PAGE_NUM_RE.match(line):
            lines.append(line)
    return lines


def _parse_date(m: re.Match) -> date:
    """
    Build a date from a regex match produced by DATE_LINE_RE or HERITAGE_DATE_RE.

    Group layout (same for both patterns):
      group(1) = month name (e.g. 'April')
      group(2) = day (e.g. '28')
      group(3) = year (e.g. '2015')
    """
    return date(
        int(m.group(3)),
        _MONTH_MAP[m.group(1).lower()[:3]],
        int(m.group(2)),
    )


def _extract_case_name(lines: list[str]) -> str | None:
    """
    Extract the lead petitioner name from a list of cleaned page lines.

    Finds the line containing 'SUPREME COURT OF THE UNITED STATES', skips
    any CAPTION_SEP_RE separator lines, then accumulates name lines until
    hitting a 'v.', 'Petitioner', or separator line. Trailing caption
    punctuation is stripped via CAPTION_PUNCT_RE. Returns None if no
    SCOTUS header is found or no name lines are accumulated.
    """
    scotus_idx = next(
        (i for i, line in enumerate(lines)
         if "SUPREME COURT OF THE UNITED STATES" in line.upper()),
        -1,
    )
    if scotus_idx == -1:
        return None

    # Skip any separator lines immediately after the SCOTUS header
    i = scotus_idx + 1
    while i < len(lines) and CAPTION_SEP_RE.match(lines[i]):
        i += 1

    # Accumulate petitioner name lines
    name_parts = []
    for line in lines[i:]:
        if (
            re.match(r'^v\.?\s*[:).]?', line, re.IGNORECASE) and len(line) <= 5
            or re.match(r'^v\.\s*$', line, re.IGNORECASE)
            or re.match(r'^Petitioner', line, re.IGNORECASE)
            or CAPTION_SEP_RE.match(line)
        ):
            break
        clean = CAPTION_PUNCT_RE.sub('', line).strip()
        if clean:
            name_parts.append(clean)

    return " ".join(name_parts) if name_parts else None


def _toc_last_name(line: str) -> str | None:
    """
    Extract the last name from a TOC 'ESQ.' line.

    'MARY L. BONAUTO, ESQ.'             → 'BONAUTO'
    'GEN. DONALD B. VERRILLI, JR., ESQ.' → 'VERRILLI'
    """
    line = re.sub(r'^(?:GEN|MR|MS|MRS|DR)\.\s+', '', line.strip(), flags=re.IGNORECASE)
    # Remove JR./SR./III./etc. suffix before ESQ.
    line = re.sub(
        r',\s*(?:JR|SR|III|II|IV)\.?,\s*ESQ(?:UIRE)?\.?\s*$', '', line, flags=re.IGNORECASE
    )
    # Remove trailing ESQ. or ESQUIRE
    line = re.sub(r',?\s*ESQ(?:UIRE)?\.?\s*$', '', line, flags=re.IGNORECASE)
    parts = line.strip().split()
    return parts[-1].rstrip(',').upper() if parts else None


def _normalize_label_last_name(raw_label: str) -> str | None:
    """
    Extract last name component from a raw_speaker_label.

    'MR. FRIEDMAN'   → 'FRIEDMAN'
    'MS. BONAUTO'    → 'BONAUTO'
    'GEN. VERRILLI'  → 'VERRILLI'
    'GENERAL VERRILLI' → 'VERRILLI'
    """
    label = re.sub(
        r'^(?:MR|MS|MRS|GENERAL|GEN)\.\s+|^GENERAL\s+',
        '',
        raw_label.strip(),
        flags=re.IGNORECASE,
    )
    parts = label.strip().split()
    return parts[-1] if parts else None


def _parse_toc_sides(lines: list[str]) -> "dict[str, str]":
    """
    Parse ESQ. name + 'On behalf of' pairs from TOC lines.

    Returns {last_name_upper: SideEnum_value} mapping. Known limitation (Pitfall 4):
    if two advocates share the same last name in one argument, the second mapping
    overwrites the first — acceptable for Phase 16 given extreme rarity.
    """
    from api.models.models import SideEnum

    mapping: dict[str, str] = {}
    pending_name: str | None = None

    for line in lines:
        if TOC_ESQ_RE.match(line):
            last = _toc_last_name(line)
            pending_name = last.upper() if last else None
            continue

        if pending_name:
            if TOC_AMICUS_RE.search(line):
                mapping[pending_name] = SideEnum.AMICUS.value
                pending_name = None
            elif m := TOC_SIDE_RE.search(line):
                role_word = m.group(1).upper()
                mapping[pending_name] = (
                    SideEnum.PETITIONER.value
                    if role_word.startswith("PETITIONER")
                    else SideEnum.RESPONDENT.value
                )
                pending_name = None
            # If neither matches, keep pending_name — next line may be the side line
            # (handles multi-line amicus descriptions per Pitfall 5)

    return mapping


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def extract_cover_metadata(pdf_path: Path) -> dict:
    """
    Extract argued_date and case_name from the cover pages of a SCOTUS transcript PDF.

    Reads pages 0–2 (the cover, case caption, and TOC pages that extract_pages skips).
    Returns a dict with zero, one, or two keys:
      - 'argued_date' → datetime.date
      - 'case_name'   → str

    Never raises — returns {} (or a partial result) on any failure (D-05).
    The parse step continues normally if extraction fails; existing DB values
    remain unchanged.
    """
    result: dict = {}
    try:
        with pdfplumber.open(pdf_path) as pdf:
            raws = [
                pdf.pages[i].extract_text(layout=False) or ""
                for i in range(min(3, len(pdf.pages)))
            ]
        for raw in raws:
            if "argued_date" not in result:
                m = DATE_LINE_RE.search(raw) or HERITAGE_DATE_RE.search(raw)
                if m:
                    result["argued_date"] = _parse_date(m)
            if "case_name" not in result:
                name = _extract_case_name(_clean_lines(raw))
                if name:
                    result["case_name"] = name
            if len(result) == 2:
                break
    except Exception:
        pass  # D-05: never raise; caller receives partial result or {}
    return result


def extract_advocate_sides(pdf_path: Path) -> "dict[str, str]":
    """
    Build a last_name_upper → SideEnum_value mapping from the TOC page.

    Scans pages 0–3 for the page containing 'C O N T E N T S', then parses
    ESQ. name + 'On behalf of' line pairs. Returns {} on any failure (D-09).

    The parse step continues normally if side extraction fails; all
    argument_participants rows stay UNKNOWN and the operator assigns via
    the Phase 15 advocate role dropdown.
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i in range(min(4, len(pdf.pages))):
                raw = pdf.pages[i].extract_text(layout=False) or ""
                if "C O N T E N T S" in raw:
                    return _parse_toc_sides(_clean_lines(raw))
    except Exception:
        pass  # D-09: never raise
    return {}
