"""
PDF text extractor for SCOTUS oral argument transcripts.

Copied exactly from spike findings:
  .claude/skills/spike-findings-scotuschat/references/pdf-extraction.md

Tested on 4 transcripts:
  - Obergefell v. Hodges Q1 (2015, Alderson Reporting)
  - Masterpiece Cakeshop (2017, Heritage)
  - Dobbs v. Jackson (2021, Heritage)
  - United States v. Rahimi (2023, Heritage)
"""

import re
from pathlib import Path

import pdfplumber

# ---------------------------------------------------------------------------
# Regex constants — copy exactly from spike
# ---------------------------------------------------------------------------

# Strip legal transcript line numbers from left margin (1–25 per page)
LINE_NUM_RE = re.compile(r"^\s{0,3}(\d{1,2})\s")

# Skip header/footer lines (reporter name, "Official", etc.)
HEADER_RE = re.compile(
    r"^(?:Official|ALDERSON|Heritage|HERITAGE|Alderson|www\.|http|\(202\)|\d{3,4}\s+L\s+Street)",
    re.IGNORECASE,
)

# Skip bare page-number lines
PAGE_NUM_RE = re.compile(r"^\d+$")

# Detect word-index pages: "word [N] page:line" entries
WORD_INDEX_RE = re.compile(r"^\w[\w\s,'.\-]{0,30}\s+\[\d+\]\s+\d+:\d+")


# ---------------------------------------------------------------------------
# Extraction functions — copy exactly from spike
# ---------------------------------------------------------------------------


def _is_word_index_page(raw_text: str) -> bool:
    """
    Returns True if this PDF page looks like the alphabetical word index
    at the back of SCOTUS transcripts.

    3+ lines matching "word [N] page:line" → word-index page.
    """
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    hits = sum(1 for l in lines if WORD_INDEX_RE.match(l))
    return hits >= 3


def strip_line_number(line: str) -> str:
    """Strip the left-margin line number (1–25) from a transcript line."""
    m = LINE_NUM_RE.match(line)
    return line[m.end() - 1:].strip() if m else line.strip()


def extract_pages(pdf_path: Path) -> list[str]:
    """
    Return cleaned text for each argument page.

    Skips the first 3 pages (cover, case caption, TOC/appearances) and stops
    at the word-index page. Word-index detection is dynamic — some transcripts
    have multiple word-index pages, so a fixed end_offset is unreliable.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        List of cleaned page text strings (one per argument page).
    """
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i in range(3, len(pdf.pages)):          # skip first 3: cover, caption, TOC
            raw = pdf.pages[i].extract_text(layout=False) or ""
            if _is_word_index_page(raw):             # stop at word index
                break
            lines = []
            for raw_line in raw.split("\n"):
                line = strip_line_number(raw_line)
                if HEADER_RE.match(line) or PAGE_NUM_RE.match(line):
                    continue
                lines.append(line)
            pages.append("\n".join(lines))
    return pages


def normalize_text(text: str) -> str:
    """
    Normalize soft hyphens (U+00AD) to double-dashes before DB write.

    Soft hyphens appear in some PDF exports and must be normalized to
    prevent downstream display issues (F11 from spike failure taxonomy).
    """
    return text.replace("­", "--").strip()   # soft hyphen → double dash (F11)
