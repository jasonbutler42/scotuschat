# Phase 16: Parser Improvements - Pattern Map

**Mapped:** 2026-06-26
**Files analyzed:** 3 (1 new module, 1 modified command, 1 new test file)
**Analogs found:** 3 / 3

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `pipeline/parser/cover_extractor.py` | utility / extractor | file-I/O + transform | `pipeline/parser/extractor.py` | exact (same role, same pdfplumber pattern) |
| `pipeline/commands/parse.py` | command / orchestrator | CRUD + file-I/O | `pipeline/commands/parse.py` (self) | self — two insertion points identified |
| `pipeline/tests/test_cover_extractor.py` | test | transform | `pipeline/tests/test_parse.py` | role-match (pure-unit pattern without DB) |

---

## Pattern Assignments

### `pipeline/parser/cover_extractor.py` (new utility module, file-I/O + transform)

**Analog:** `pipeline/parser/extractor.py`

**Module header / imports pattern** (extractor.py lines 1–18):
```python
"""
<docstring describing what PDFs are handled and which transcripts were tested>
"""

import re
from pathlib import Path

import pdfplumber

from pipeline.parser.extractor import strip_line_number
```
Copy this header structure exactly. The new module imports `strip_line_number` from `extractor.py`
(per CONTEXT.md `<code_context>`) — do not duplicate it.

**Regex constants block pattern** (extractor.py lines 20–36):
```python
# ---------------------------------------------------------------------------
# Regex constants
# ---------------------------------------------------------------------------

LINE_NUM_RE = re.compile(r"^\s{0,3}(\d{1,2})\s")
HEADER_RE = re.compile(
    r"^(?:Official|ALDERSON|Heritage|HERITAGE|Alderson|www\.|http|\(202\)|\d{3,4}\s+L\s+Street)",
    re.IGNORECASE,
)
PAGE_NUM_RE = re.compile(r"^\d+$")
```
The new module re-uses `HEADER_RE` and `PAGE_NUM_RE` constants from `extractor.py` — import them
rather than redefining. Add the Phase 16-specific constants below them in the same sectioned style:

```python
# Cover page — date patterns
DATE_LINE_RE = re.compile(
    r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+'
    r'(January|February|March|April|May|June|July|August|September|October|November|December)'
    r'\s+(\d{1,2}),\s+(\d{4})',
    re.IGNORECASE,
)
HERITAGE_DATE_RE = re.compile(
    r'Date:\s+'
    r'(January|February|March|April|May|June|July|August|September|October|November|December)'
    r'\s+(\d{1,2}),\s+(\d{4})',
    re.IGNORECASE,
)
CAPTION_SEP_RE = re.compile(r'^[\xad\-\s–—xX\*]+$')
CAPTION_PUNCT_RE = re.compile(r'\s*[:),]\s*$')

# TOC page — advocate side patterns
TOC_ESQ_RE = re.compile(
    r'^(?:(?:GEN|MR|MS|MRS|DR)\.\s+)?[A-Z][A-Z\s.,]+,\s*ESQ(?:UIRE)?\.?\s*$',
    re.IGNORECASE,
)
TOC_SIDE_RE = re.compile(
    r'[Oo]n behalf of(?:\s+the)?\s+(Petitioner|Respondent|Petitioners|Respondents)',
    re.IGNORECASE,
)
TOC_AMICUS_RE = re.compile(r'amicus\s+curiae', re.IGNORECASE)

_MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
```

**Extraction function pattern** (extractor.py lines 62–89 — `extract_pages`):
```python
def extract_pages(pdf_path: Path) -> list[str]:
    """
    <docstring>
    """
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i in range(3, len(pdf.pages)):
            raw = pdf.pages[i].extract_text(layout=False) or ""
            ...
            lines.append(line)
        pages.append(normalize_text("\n".join(lines)))
    return pages
```
New functions follow the same shape: `pdfplumber.open()` as context manager, `extract_text(layout=False)`,
loop over page indices, call `strip_line_number()` on each raw line. Never open PDF outside the `with` block.

**Fail-safe pattern** — both new public functions wrap everything in `try / except Exception: pass` and
return an empty dict on any failure. This is the D-05 / D-09 contract. No other exception handling style is
used in this module.

```python
def extract_cover_metadata(pdf_path: Path) -> dict:
    """Returns dict with 0-2 keys: 'argued_date' (date) and 'case_name' (str).
    Never raises — returns {} on any failure (D-05)."""
    result: dict = {}
    try:
        with pdfplumber.open(pdf_path) as pdf:
            raws = [pdf.pages[i].extract_text(layout=False) or ""
                    for i in range(min(3, len(pdf.pages)))]
        ...
    except Exception:
        pass
    return result


def extract_advocate_sides(pdf_path: Path) -> dict[str, str]:
    """Returns {last_name_upper: SideEnum_value}. Returns {} on failure (D-09)."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i in range(min(4, len(pdf.pages))):
                raw = pdf.pages[i].extract_text(layout=False) or ""
                if "C O N T E N T S" in raw:
                    ...
                    return mapping
    except Exception:
        pass
    return {}
```

**Private helper pattern** (extractor.py `_is_word_index_page`, lines 44–53):
```python
def _is_word_index_page(raw_text: str) -> bool:
    """<single responsibility docstring>"""
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    hits = sum(1 for l in lines if WORD_INDEX_RE.match(l))
    return hits >= 3
```
Private helpers use underscore prefix and a single-sentence docstring. Phase 16 adds:
`_get_clean_lines`, `_parse_date`, `_extract_case_name`, `_toc_last_name`,
`_normalize_label_last_name`, `_parse_toc_sides` — all follow this same style.

---

### `pipeline/commands/parse.py` (modified — two insertion points)

**Analog:** `pipeline/commands/parse.py` (self)

**Import block** (parse.py lines 28–44) — add two new imports to the existing block:
```python
from pipeline.parser.cover_extractor import extract_cover_metadata, extract_advocate_sides
```
Also ensure `Argument`, `Case`, `CaseArgument` are imported from `api.models.models`. Check line 31–40;
add any missing models to the existing import tuple.

**Insertion point 1 — after `extract_pages()` call (parse.py lines 139–141), before `parse_transcript`:**
```python
# Existing:
pages = extract_pages(pdf_path)
pages = [_normalize_dashes(p) for p in pages]
print(f"Extracted {len(pages)} argument pages.")

# INSERT HERE — Phase 16 PARSE-01 (CPU only, before session writes, before dry-run gate):
cover_meta = extract_cover_metadata(pdf_path)
advocate_sides = extract_advocate_sides(pdf_path)
if cover_meta:
    print(f"Cover metadata extracted: {list(cover_meta.keys())}")
```
Call both extraction functions BEFORE the `async with get_session()` block to avoid blocking sync
I/O inside an async DB transaction (RESEARCH.md Pitfall 1). Both return dicts; pass them through
to the session write block below.

**Dry-run gate pattern** (parse.py lines 212–215):
```python
if args.dry_run:
    print(f"Dry-run mode: {len(utterances)} utterances parsed but NOT written to DB.")
    print(f"Parse dry-run complete.")
    return
```
Metadata DB writes (UPDATE statements) must come AFTER this gate — same as utterance writes. The
extraction calls (CPU-only) go before the gate; session.execute(update(...)) calls go after it.

**Insertion point 2 — after step 7b flush (parse.py line 281), before step 8:**
```python
# After existing step 7b flush:
await session.flush()
print(f"Seeded {len(new_rows)} argument_participant row(s) ...")

# INSERT HERE — Phase 16 PARSE-01 metadata writes:
if cover_meta.get("argued_date") is not None:
    await session.execute(
        update(Argument)
        .where(Argument.id == source_run.argument_id)
        .values(argued_date=cover_meta["argued_date"])
        .execution_options(synchronize_session=False)
    )

if cover_meta.get("case_name") is not None:
    result = await session.execute(
        select(CaseArgument.case_id)
        .where(
            CaseArgument.argument_id == source_run.argument_id,
            CaseArgument.is_lead == True,
        )
    )
    lead_row = result.first()
    if lead_row:
        await session.execute(
            update(Case)
            .where(Case.id == lead_row.case_id)
            .values(case_name=cover_meta["case_name"])
            .execution_options(synchronize_session=False)
        )

# INSERT HERE — Phase 16 PARSE-02 side detection writes:
if advocate_sides and run.argument_id is not None:
    await _update_participant_sides(session, run.argument_id, advocate_sides)
```

**SQLAlchemy async update pattern** (parse.py lines 106–113 — AdminJob update):
```python
await session.execute(
    update(AdminJob)
    .where(AdminJob.id == args.job_id)
    .values(
        status=AdminJobStatus.RUNNING,
        current_step=AdminJobStep.PARSE,
    )
    .execution_options(synchronize_session=False)
)
```
All UPDATE calls in this project use `update(Model).where(...).values(...).execution_options(synchronize_session=False)`.
Never use `session.merge()` or direct attribute assignment + flush for non-ORM-tracked objects.

**select() pattern** (parse.py lines 267–272 — ArgumentParticipant select):
```python
existing_result = await session.execute(
    select(ArgumentParticipant.raw_speaker_label).where(
        ArgumentParticipant.argument_id == run.argument_id
    )
)
existing = {row[0] for row in existing_result.all()}
```
Use `select(Model.column).where(...)` for scalar-column selects; use `.scalars().all()` for full
ORM object fetches. Phase 16 CaseArgument lookup uses the scalar-column form.

**Print logging pattern** (parse.py lines 139, 147, 178, etc.):
```python
print(f"Extracting pages from {pdf_path} ...")
print(f"Extracted {len(pages)} argument pages.")
print(f"Running rule-based state machine parser ...")
```
All pipeline progress is logged with `print()` f-strings — no logging framework. Phase 16 additions
follow this pattern: `print(f"Cover metadata extracted: ...")`, `print(f"Advocate sides mapped: ...")`.

---

### `pipeline/tests/test_cover_extractor.py` (new test file, pure-unit)

**Analog:** `pipeline/tests/test_parse.py`

**File header pattern** (test_parse.py lines 1–16):
```python
"""
<Description of what is tested and what test IDs from VALIDATION.md are covered.>

These tests do NOT require a database — they exercise pipeline/parser/<module>.py
directly using in-memory <input>.

Test IDs covered:
  - PARSE-01: ...
  - PARSE-02: ...
"""

import pytest
```

**Sync test structure pattern** (test_parse.py lines 35–79):
```python
def test_<feature>():
    """<One-line description of the invariant under test>."""
    from pipeline.parser.<module> import <function>

    # Arrange
    <input data>

    # Act
    result = <function>(input)

    # Assert with descriptive failure messages
    assert <condition>, (
        f"<Human-readable explanation of what went wrong>: "
        f"{<actual value>!r}"
    )
```
Import under test happens inside the test function (not at module level) — matches existing style.
Assertion messages use f-strings with `!r` repr for actual values.

**Monkeypatching pattern** (test_parse.py lines 108–127):
```python
def mock_extract_pages(pdf_path):
    return ["CHIEF JUSTICE ROBERTS: We will hear argument now.\n"]

monkeypatch.setattr(
    "pipeline.commands.parse.extract_pages",
    mock_extract_pages,
)
```
For unit tests of cover_extractor.py, no monkeypatching is needed — the functions accept a
`pdf_path: Path` and open the PDF themselves. Tests should use real PDFs from `data/pdfs/` for
integration assertions, or construct minimal synthetic pages as strings and test private helpers
(`_get_clean_lines`, `_extract_case_name`, `_parse_toc_sides`) directly without opening a PDF.

**Test for private helper (preferred pattern for cover_extractor unit tests):**
```python
def test_extract_case_name_alderson():
    """Case name extracted correctly from Alderson-format cover page lines."""
    from pipeline.parser.cover_extractor import _extract_case_name

    lines = [
        "IN THE SUPREME COURT OF THE UNITED STATES",
        "\xad \xad \xad \xad \xad \xad \xad \xad x",
        "JAMES OBERGEFELL, ET AL.,",
        "Petitioners,",
    ]
    result = _extract_case_name(lines)
    assert result == "JAMES OBERGEFELL, ET AL.", f"Got: {result!r}"
```

---

## Shared Patterns

### Async SQLAlchemy UPDATE
**Source:** `pipeline/commands/parse.py` lines 106–113 and 287–288
**Apply to:** Both metadata write blocks in `_run_parse_inner`
```python
await session.execute(
    update(Model)
    .where(Model.id == target_id)
    .values(field=value)
    .execution_options(synchronize_session=False)
)
```
Never omit `.execution_options(synchronize_session=False)` — it is the project-standard for all
bulk/targeted UPDATE calls in the pipeline.

### Fail-Safe Extract Pattern
**Source:** Established by D-05 / D-09 in CONTEXT.md; structural pattern from `extractor.py`
**Apply to:** All public functions in `cover_extractor.py`
```python
def extract_<something>(pdf_path: Path) -> dict:
    result = {}
    try:
        ...  # all pdfplumber and regex logic
    except Exception:
        pass  # never raise — return partial result or {}
    return result
```
No logging of the exception — silent fail is the contract. If debug visibility is needed later, a
future phase can add logging; Phase 16 matches the existing extractor.py silent-pass style.

### Dry-Run Gate
**Source:** `pipeline/commands/parse.py` lines 212–215
**Apply to:** All three DB writes added in Phase 16 (argued_date UPDATE, case_name UPDATE,
side UPDATE). All must be placed in the code path AFTER line 215.
```python
if args.dry_run:
    print(f"Dry-run mode: ...")
    return  # ← Phase 16 DB writes must never appear before this return
```

### pdfplumber Open Pattern
**Source:** `pipeline/parser/extractor.py` lines 77–89
**Apply to:** `extract_cover_metadata` and `extract_advocate_sides` in `cover_extractor.py`
```python
with pdfplumber.open(pdf_path) as pdf:
    raw = pdf.pages[i].extract_text(layout=False) or ""
```
Always `or ""` for null safety. Always use `layout=False` (matches existing `extract_pages` call).
Always use the context manager form — never assign `pdfplumber.open(...)` to a variable directly.

---

## No Analog Found

None — all three files have strong analogs in the codebase.

---

## Metadata

**Analog search scope:** `pipeline/parser/`, `pipeline/commands/`, `pipeline/tests/`
**Files scanned:** 4 (`extractor.py`, `parse.py`, `test_parse.py`, `models.py` lines 130–250)
**Pattern extraction date:** 2026-06-26
