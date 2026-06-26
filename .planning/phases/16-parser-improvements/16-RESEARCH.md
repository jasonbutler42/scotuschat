# Phase 16: Parser Improvements - Research

**Researched:** 2026-06-26
**Domain:** PDF cover-page metadata extraction + SQLAlchemy async UPDATE patterns
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Extraction is regex-only — no LLM call for cover page metadata.
- **D-02:** Writes `argued_date` to the `Argument` record (direct UPDATE on the existing row).
- **D-03:** Writes `case_name` to the lead Case row only — `case_arguments.is_lead = True` for this `argument_id`.
- **D-04:** Always overwrite — parse step writes extracted values unconditionally on every run.
- **D-05:** Failure fallback — if regex returns `None`, skip that field (no write). Parse step never raises because of metadata extraction.
- **D-06:** Source of truth for advocate sides is the TOC/appearances page, which contains `On behalf of PETITIONER/RESPONDENT` lines.
- **D-07:** Build a `raw_speaker_label → SideEnum` mapping from the TOC page. UPDATE `argument_participants SET side = <value> WHERE argument_id = X AND raw_speaker_label = <label>`.
- **D-08:** Unmatched participants stay `UNKNOWN`. Partial updates accepted.
- **D-09:** If TOC yields zero mappings, skip UPDATE entirely. Parse step never fails because of side extraction.

### Claude's Discretion

- Exact regex patterns for cover page (case name line format, date line format).
- Speaker label matching strategy for TOC → `argument_participants`.
- Which of pages 0–2 contains each piece of data (researcher confirms).
- Whether to add a new helper module or extend `extractor.py` directly.

### Deferred Ideas (OUT OF SCOPE)

- Updating `docket_number` / `docket_number_norm` on Case rows (set at ingest).
- Consolidated docket handling — updating all case rows, not just the lead.
- LLM-assisted extraction for non-standard formats.
- Extraction confidence / audit log.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PARSE-01 | Parse step automatically extracts case name, docket number, and argued date from the transcript PDF and pre-populates argument metadata fields | Cover-page structure confirmed across 9 real PDFs; regex patterns validated against all formats; INSERT slot in `_run_parse_inner` identified (between steps 3 and 7) |
| PARSE-02 | Parse step automatically detects which side each advocate is arguing from the transcript structure and stores it as the initial per-argument role | TOC page structure confirmed; last-name matching strategy validated; UPDATE slot identified (after step 7b, within same session) |
</phase_requirements>

---

## Summary

Phase 16 extends the existing `pipeline/commands/parse.py` `_run_parse_inner` function with two extraction passes that read the cover pages (currently skipped by `extract_pages`) and write results to existing database columns. No schema changes. No new migrations. No LLM calls.

**PARSE-01 (cover-page metadata)** adds a `extract_cover_metadata(pdf_path)` function that opens the same PDF pdfplumber already opens, reads pages 0–2, and extracts `argued_date` and `case_name` using regex. The `argued_date` is written to the `Argument` row via SQLAlchemy `update()`. The `case_name` is written to the `Case` row linked via `CaseArgument.is_lead = True`. Both writes are unconditional (D-04) and fail-safe (D-05).

**PARSE-02 (advocate side detection)** adds a `extract_advocate_sides(pdf_path)` function that scans the TOC page (the page containing `C O N T E N T S`) within pages 0–3 of the PDF, builds a last-name → `SideEnum` map from the `ESQ.` + `On behalf of` line pairs, then matches against `argument_participants.raw_speaker_label` using last-name normalization. Updates are issued as a bulk `update()` per matched participant.

**Primary recommendation:** Add a new `pipeline/parser/cover_extractor.py` module (rather than extending `extractor.py`) so the two concerns stay separated and `extractor.py` remains unchanged. Call the new functions from `_run_parse_inner` in two insertion points: cover metadata immediately after `extract_pages()` (step 3), and side detection after step 7b (after `argument_participants` rows are seeded).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| PDF cover page text extraction | Pipeline CLI | — | pdfplumber already in pipeline; no web tier involvement |
| Regex-based metadata parsing | Pipeline CLI | — | Pure Python, no DB or network |
| Argument.argued_date UPDATE | Pipeline CLI → PostgreSQL | — | Pipeline writes directly to DB per CLAUDE.md architecture rule 1 |
| Case.case_name UPDATE (lead) | Pipeline CLI → PostgreSQL | — | JOIN through CaseArgument.is_lead; same session as utterance writes |
| argument_participants.side UPDATE | Pipeline CLI → PostgreSQL | — | After step 7b seeds the rows; same async session, same transaction |
| Dry-run gate | Pipeline CLI | — | All three writes guarded by existing `args.dry_run` check (CR-05) |

---

## Standard Stack

### Core (no new packages — all already installed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pdfplumber` | already installed | PDF text extraction from cover pages | Mandated by PIPE-03; proven across 9 transcripts |
| `re` (stdlib) | Python 3.12 | Regex extraction | No external dep needed; patterns are simple |
| `sqlalchemy` (async) | already installed | `update()` + `select()` for DB writes | Project-standard ORM; `AsyncSession` already in use |
| `datetime` (stdlib) | Python 3.12 | `date.fromisoformat()` / `datetime.strptime()` for date construction | Stdlib; consistent with existing parse.py usage |

No new packages. No package legitimacy audit required.

---

## Package Legitimacy Audit

Not applicable — Phase 16 introduces no new external dependencies.

---

## Architecture Patterns

### System Architecture Diagram

```
PDF file (immutable)
     |
     v
pdfplumber.open(pdf_path)  ← single open pass
     |
     +─── pages 0-2 ──→ cover_extractor.extract_cover_metadata()
     |                        |
     |                        +─→ DATE_RE → argued_date (date obj or None)
     |                        +─→ case name extraction → case_name (str or None)
     |                        |
     |                        v
     |               [if not dry_run AND not None]
     |               UPDATE arguments SET argued_date = X WHERE id = argument_id
     |               SELECT case_id via CaseArgument.is_lead = True
     |               UPDATE cases SET case_name = X WHERE id = case_id
     |
     +─── pages 3+ ──→ extract_pages() [existing] → parse_transcript() → utterances
     |
     v
Step 7b: seed argument_participants rows
     |
     v
cover_extractor.extract_advocate_sides()
     |
     +─→ scan pages 0-3 for TOC page (contains 'C O N T E N T S')
     +─→ parse ESQ. lines + following 'On behalf of' lines → {last_name: SideEnum}
     +─→ for each argument_participant: normalize label last name, lookup side
     |
     v
[if not dry_run AND mappings found]
UPDATE argument_participants SET side = X WHERE argument_id = Y AND raw_speaker_label = Z
     |
     v
Step 8: transition running → completed
```

### Recommended Module Structure

```
pipeline/
├── parser/
│   ├── extractor.py          # UNCHANGED — extract_pages, strip_line_number, normalize_text
│   ├── cover_extractor.py    # NEW — extract_cover_metadata(), extract_advocate_sides()
│   ├── state_machine.py      # unchanged
│   └── llm_pass.py           # unchanged
├── commands/
│   └── parse.py              # MODIFIED — two new call sites in _run_parse_inner
└── tests/
    └── test_cover_extractor.py  # NEW — unit tests for both new functions
```

### Pattern 1: Single PDF Open Pass

The pdfplumber context in `_run_parse_inner` is currently scoped only to `extract_pages()`. Since `extract_cover_metadata()` and `extract_advocate_sides()` also need the PDF, two approaches are valid:

**Option A (cleaner, preferred):** Have `extract_cover_metadata(pdf_path)` and `extract_advocate_sides(pdf_path)` each open the PDF independently. pdfplumber opens are cheap (no rendering); the PDF is already on disk and immutable. This keeps function signatures simple and the two new functions completely self-contained.

**Option B (one open pass):** Pass `pdf.pages[0:3]` pre-extracted text into the new functions. Saves one file open call at the cost of tighter coupling.

CONTEXT.md `<specifics>` recommends a single open pass, but D-01 and D-09 both make the functions self-contained fail-safe units. **Recommendation: Option A** — each new function opens the PDF itself. The overhead is negligible and isolation is worth more than micro-optimization.

```python
# Source: direct codebase read of pipeline/parser/extractor.py + pipeline/commands/parse.py
# Pattern: how extract_pages is called in _run_parse_inner
pages = extract_pages(pdf_path)

# New calls (insert immediately after, before parse_transcript):
cover_meta = extract_cover_metadata(pdf_path)    # returns dict or {}
advocate_sides = extract_advocate_sides(pdf_path) # returns dict or {}
```

### Pattern 2: Regex Patterns (VERIFIED against 9 real PDFs)

```python
# Source: validated by executing against data/pdfs/*.pdf in this research session

import re
from datetime import date

# Date line — matches both Alderson and Heritage inline formats
# Alderson: 'Tuesday, April 28, 2015'
# Heritage inline: 'Wednesday, April 24, 2024'
DATE_LINE_RE = re.compile(
    r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+'
    r'(January|February|March|April|May|June|July|August|September|October|November|December)'
    r'\s+(\d{1,2}),\s+(\d{4})',
    re.IGNORECASE,
)

# Heritage cover-page (page 0, no line numbers) date format
# 'Date: April 24, 2024'
HERITAGE_DATE_RE = re.compile(
    r'Date:\s+'
    r'(January|February|March|April|May|June|July|August|September|October|November|December)'
    r'\s+(\d{1,2}),\s+(\d{4})',
    re.IGNORECASE,
)

# Case name extraction: separator line (soft-hyphen or dash based)
# Alderson uses soft-hyphen (\xad) separated by spaces; Heritage uses dashes
CAPTION_SEP_RE = re.compile(r'^[\xad\-\s–—xX\*]+$')

# Trailing case-caption punctuation to strip from name lines: ' :' ' )' ' ,' 
CAPTION_PUNCT_RE = re.compile(r'\s*[:),]\s*$')

# TOC advocate name line: 'MARY L. BONAUTO, ESQ.' or 'GEN. DONALD B. VERRILLI, JR., ESQ.'
TOC_ESQ_RE = re.compile(
    r'^(?:(?:GEN|MR|MS|MRS|DR)\.\s+)?'
    r'([A-Z][A-Z\s.,]+?),\s*ESQ(?:UIRE)?\.?\s*$',
    re.IGNORECASE,
)

# TOC side attribution line: 'On behalf of the Petitioner 3' / 'On behalf of Respondents...'
TOC_SIDE_RE = re.compile(
    r'[Oo]n behalf of(?:\s+the)?\s+(Petitioner|Respondent|Petitioners|Respondents)',
    re.IGNORECASE,
)

# TOC amicus line: 'For the United States, as amicus curiae' / 'as amicus curiae'
TOC_AMICUS_RE = re.compile(r'amicus\s+curiae', re.IGNORECASE)
```

### Pattern 3: Cover Page Extraction

```python
# Source: validated against all 9 PDFs in data/pdfs/
# Key structural finding (VERIFIED):
# - Alderson: date on page 0 or page 1; 'C O N T E N T S' on page 1 or page 2
# - Heritage: 'Date: ...' on page 0 (no line numbers); date repeated on page 1
# - Case name: always follows 'IN THE SUPREME COURT OF THE UNITED STATES' header
#   then a separator line, then the first petitioner name line(s)

from pipeline.parser.extractor import strip_line_number
import pdfplumber

HEADER_RE = re.compile(
    r'^(?:Official|ALDERSON|Heritage|HERITAGE|Alderson|www\.|http|\(202\)|'
    r'\d{3,4}\s+L\s+Street|SUPREME\s+COURT)',
    re.IGNORECASE,
)
PAGE_NUM_RE = re.compile(r'^\d+$')

def _get_clean_lines(raw_text: str) -> list[str]:
    """Strip line numbers, headers, footers from a page's raw text."""
    lines = []
    for raw_line in raw_text.split("\n"):
        line = strip_line_number(raw_line).strip()
        if line and not HEADER_RE.match(line) and not PAGE_NUM_RE.match(line):
            lines.append(line)
    return lines

def extract_cover_metadata(pdf_path: Path) -> dict:
    """
    Extract argued_date and case_name from the cover pages of a SCOTUS PDF.
    
    Returns dict with zero or more of: {'argued_date': date, 'case_name': str}
    Never raises — returns {} on any failure.
    """
    result = {}
    try:
        with pdfplumber.open(pdf_path) as pdf:
            cover_pages = [
                (pdf.pages[i].extract_text(layout=False) or "")
                for i in range(min(3, len(pdf.pages)))
            ]
        
        # --- Extract argued_date ---
        for raw in cover_pages:
            m = DATE_LINE_RE.search(raw) or HERITAGE_DATE_RE.search(raw)
            if m:
                month_str, day_str, year_str = m.group(1), m.group(2), m.group(3)
                result["argued_date"] = date(
                    int(year_str),
                    _MONTH_MAP[month_str.lower()[:3]],
                    int(day_str),
                )
                break
        
        # --- Extract case_name ---
        for raw in cover_pages:
            lines = _get_clean_lines(raw)
            name = _extract_case_name_from_lines(lines)
            if name:
                result["case_name"] = name
                break
    
    except Exception:
        pass  # D-05: never raise
    
    return result
```

### Pattern 4: DB Write — Argument.argued_date

```python
# Source: direct read of pipeline/commands/parse.py + api/models/models.py
# Pattern: SQLAlchemy async update() with synchronize_session=False (already used in parse.py)
from sqlalchemy import select, update

# In _run_parse_inner, after dry_run check, within the async session:
if cover_meta.get("argued_date") is not None and not args.dry_run:
    await session.execute(
        update(Argument)
        .where(Argument.id == source_run.argument_id)
        .values(argued_date=cover_meta["argued_date"])
        .execution_options(synchronize_session=False)
    )

if cover_meta.get("case_name") is not None and not args.dry_run:
    # Find the lead case_id
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
```

### Pattern 5: TOC-Based Side Mapping + argument_participants UPDATE

```python
# Source: validated against all 9 PDFs in data/pdfs/
# TOC page structure (VERIFIED):
# 1. The page containing 'C O N T E N T S' is the TOC — scan pages 0-3
# 2. Lines alternate: ESQ. name line → 'On behalf of ...' line
# 3. Match by last name: 'BONAUTO, ESQ.' → last name = 'BONAUTO'
#    body label 'MS. BONAUTO' → last name = 'BONAUTO'
# 4. GEN. prefix in TOC is stripped before last name extraction
# 5. 'JR.' suffix before ESQ. must be handled: 'VERRILLI, JR., ESQ.' → 'VERRILLI'

def _extract_last_name_from_toc(esq_line: str) -> str | None:
    """
    Extract the last name from a TOC 'ESQ.' line.
    'MARY L. BONAUTO, ESQ.' -> 'BONAUTO'
    'GEN. DONALD B. VERRILLI, JR., ESQ.' -> 'VERRILLI'
    """
    # Strip GEN./MR./MS. prefix
    esq_line = re.sub(r'^(?:GEN|MR|MS|MRS|DR)\.\s+', '', esq_line.strip(), flags=re.IGNORECASE)
    # Remove ESQ. and JR./SR. suffixes
    esq_line = re.sub(r',\s*(?:JR|SR|III|II|IV)\.?,\s*ESQ(?:UIRE)?\.?\s*$', '', esq_line, flags=re.IGNORECASE)
    esq_line = re.sub(r',?\s*ESQ(?:UIRE)?\.?\s*$', '', esq_line, flags=re.IGNORECASE)
    # Last token of remaining text is the last name
    parts = esq_line.strip().split()
    return parts[-1].rstrip(',') if parts else None

def _normalize_label_last_name(raw_label: str) -> str | None:
    """
    Extract last name from a raw_speaker_label.
    'MR. FRIEDMAN' -> 'FRIEDMAN'
    'MS. BONAUTO' -> 'BONAUTO'
    'GEN. VERRILLI' -> 'VERRILLI'  (though parse.py uses GENERAL not GEN.)
    'GENERAL VERRILLI' -> 'VERRILLI'
    """
    label = re.sub(r'^(?:MR|MS|MRS|GENERAL|GEN)\.\s+', '', raw_label.strip(), flags=re.IGNORECASE)
    label = re.sub(r'^GENERAL\s+', '', label.strip(), flags=re.IGNORECASE)
    parts = label.strip().split()
    return parts[-1] if parts else None

def extract_advocate_sides(pdf_path: Path) -> dict[str, str]:
    """
    Build {last_name_upper: SideEnum_value} from the TOC page.
    Returns {} on any failure (D-09).
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i in range(min(4, len(pdf.pages))):
                raw = pdf.pages[i].extract_text(layout=False) or ""
                if "C O N T E N T S" in raw:
                    return _parse_toc_sides(_get_clean_lines(raw))
    except Exception:
        pass
    return {}

def _parse_toc_sides(lines: list[str]) -> dict[str, str]:
    """Parse ESQ. name + 'On behalf of' pairs from TOC lines."""
    from api.models.models import SideEnum
    mapping = {}
    pending_name = None  # last name from most recent ESQ. line
    
    for line in lines:
        esq_m = TOC_ESQ_RE.match(line)
        if esq_m:
            last = _extract_last_name_from_toc(line)
            pending_name = last.upper() if last else None
            continue
        
        if pending_name:
            amicus_m = TOC_AMICUS_RE.search(line)
            side_m = TOC_SIDE_RE.search(line)
            
            if amicus_m:
                mapping[pending_name] = SideEnum.AMICUS.value
                pending_name = None
            elif side_m:
                role_word = side_m.group(1).upper()
                if role_word.startswith("PETITIONER"):
                    mapping[pending_name] = SideEnum.PETITIONER.value
                else:
                    mapping[pending_name] = SideEnum.RESPONDENT.value
                pending_name = None
            # If neither matches, keep pending_name — next line may be the side line
    
    return mapping
```

### Anti-Patterns to Avoid

- **Opening the PDF inside the async session context**: pdfplumber is sync I/O. Call `extract_cover_metadata()` and `extract_advocate_sides()` before entering the async session (or extract the text before the session, passing text in). Do NOT call synchronous pdfplumber inside an async context that holds a DB transaction open — this is a blocking call.
- **Using page 2 as a hardcoded TOC page**: The TOC is on different pages across formats (page 1, 2, or 3). Always scan for `C O N T E N T S` dynamically.
- **Direct string equality matching for speaker labels**: `'MARY L. BONAUTO, ESQ.'` never equals `'MS. BONAUTO'`. Always extract last name from both sides before comparing.
- **Assuming appearances page has body-format labels**: The appearances page uses full `ESQ.` names, not the abbreviated `MR. LASTNAME` format used in the argument body. The TOC page (not the appearances page) is the right source for side detection because it pairs name + side explicitly.
- **Not guarding writes with `args.dry_run`**: The existing `dry_run` check in `_run_parse_inner` returns early before the DB session writes. Cover metadata and side updates must be inside the same post-dry-run block (or also gated by the same check). The dry-run return is currently at line 213 of `parse.py` — metadata extraction (which is CPU-only) can happen before it; DB writes must happen after it.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF text extraction | Custom PDF parser | `pdfplumber` (already installed) | Handles encoding, line numbers, multi-column; already proven on 9 transcripts |
| Async DB UPDATE | Custom SQL string | `sqlalchemy update().execution_options(synchronize_session=False)` | Consistent with existing pattern in `parse.py` (used in steps 0, 7, 8); avoids ORM cache invalidation issues |
| Date parsing | Custom string splitter | `datetime.strptime(f"{month} {day} {year}", "%B %d %Y").date()` | Handles month name → integer reliably |
| Case lead lookup | Raw SQL join | `select(CaseArgument.case_id).where(CaseArgument.is_lead == True, ...)` | Consistent with SQLAlchemy pattern already used in project |

---

## Critical Structural Findings

### Page Layout Variation (VERIFIED against 9 PDFs)

This is the most important finding for planning. **The "cover page" is not always page 0**:

| Format | Date Location | Case Name Location | TOC Location |
|--------|--------------|-------------------|--------------|
| Alderson (2006–2015), single case | Page 0 | Page 0 | Page 1 or 2 |
| Alderson (2015), multi-case (Obergefell) | Page 1 | Page 0 | Page 2 |
| Heritage (2023–2024) | Page 0 (Heritage cover) AND page 1 | Page 0 (no line numbers) or page 1 | Page 2 or 3 |

**Implication for extraction functions:**
- Scan pages 0–2 for the date (any page may have it; take first match)
- Scan pages 0–1 for the case name (SCOTUS header + first petitioner name)
- Scan pages 0–3 for the TOC page (identified by `C O N T E N T S`)

### Heritage Cover Page (Page 0) Has No Line Numbers

The Heritage cover page (page 0) is a summary sheet with no line numbers:
```
SUPREME COURT
OF THE UNITED STATES
IN THE SUPREME COURT OF THE UNITED STATES
- - - - - - - - - - - - - - - - - -
MIKE MOYLE, SPEAKER OF THE IDAHO )
HOUSE OF REPRESENTATIVES, ET AL., )
Petitioners, )
v. ) No. 23-726
...
Date: April 24, 2024
HERITAGE REPORTING CORPORATION
```
The `strip_line_number()` utility handles this correctly (no match → returns line as-is).

### Soft Hyphen Separator Lines (Alderson Format)

Alderson separator lines use soft hyphens (`\xad`), not regular ASCII hyphens:
```
'\xad \xad \xad \xad \xad \xad \xad \xad \xad \xad \xad \xad \xad \xad \xad \xad \xad x'
```
The `CAPTION_SEP_RE` must include `\xad` to correctly skip these separators and reach the case name line.

### TOC Name → Body Label Mismatch (VERIFIED)

The TOC uses full formal names (`MARY L. BONAUTO, ESQ.`) while the argument body uses abbreviated labels (`MS. BONAUTO`). Direct string matching fails. Last-name matching is the correct strategy:

| TOC Name | Body Label | Last Name Match |
|----------|-----------|-----------------|
| `MARY L. BONAUTO, ESQ.` | `MS. BONAUTO` | `BONAUTO` ✓ |
| `GEN. DONALD B. VERRILLI, JR., ESQ.` | `GEN. VERRILLI` | `VERRILLI` ✓ |
| `JOSHUA N. TURNER, ESQ.` | `MR. TURNER` | `TURNER` ✓ |
| `SHAY DVORETZKY, ESQ.` | `MR. DVORETZKY` | `DVORETZKY` ✓ |

**Risk:** Last-name collision (two advocates with the same last name in one argument). This is extremely rare in practice and the CONTEXT.md does not require handling it. If it occurs, the second advocate's mapping would overwrite the first in the dict — which is acceptable for Phase 16. Document as a known limitation.

### Heritage TOC: No `ORAL ARGUMENT OF` Prefix on Name Lines

Heritage format TOC does NOT repeat `ORAL ARGUMENT OF` before every name — only as a header:
```
ORAL ARGUMENT OF: PAGE:     ← header
SHAY DVORETZKY, ESQ.        ← name line (no ORAL ARGUMENT OF prefix)
On behalf of the Petitioner 3
ORAL ARGUMENT OF:           ← next section header
FREDERICK LIU, ESQ.
On behalf of the Respondent 59
```
Alderson alternates between including and omitting the header. The `TOC_ESQ_RE` approach (match ESQ. lines directly) handles both formats without needing to parse `ORAL ARGUMENT OF` headers.

### DB Write Placement (VERIFIED against parse.py step sequence)

```
Step 3:  extract_pages()                      ← cover_metadata extraction happens HERE (CPU only, before session writes)
Step 4:  parse_transcript()
Step 5:  LLM corrective pass
Step 6:  dry_run check ← GATE: writes only after this
Step 2d: CREATE PipelineRun row
Step 7:  Write utterance rows
Step 7b: Seed argument_participants rows
         ↑ advocate_sides UPDATE happens HERE (in same session, rows now exist)
Step 8:  Transition → completed
```

Cover metadata DB writes (argued_date, case_name) slot in between step 6 (dry-run gate) and step 7 (utterance writes), using `source_run.argument_id` which is available before the new PipelineRun row is created.

Advocate side UPDATE slots in after step 7b, using the same async session. The rows definitely exist at that point.

---

## Common Pitfalls

### Pitfall 1: Calling pdfplumber inside async DB session context
**What goes wrong:** pdfplumber file I/O blocks the event loop. If called while holding an open SQLAlchemy `AsyncSession`, it can cause apparent hangs or interfere with the async context.
**Why it happens:** `extract_cover_metadata()` and `extract_advocate_sides()` use synchronous I/O.
**How to avoid:** Call both extraction functions BEFORE entering the `async with get_session() as session:` context, or call them at the top of `_run_parse_inner` before the session opens. Pass the raw results (a dict) into the session-writing block.
**Warning signs:** Test passes in isolation but hangs under load.

### Pitfall 2: Writing to Case before verifying is_lead row exists
**What goes wrong:** A `Case` write that skips the `is_lead` guard could write to the wrong case (in consolidated arguments, multiple cases exist).
**Why it happens:** Shortcutting the `CaseArgument` join.
**How to avoid:** Always `SELECT case_id FROM case_arguments WHERE argument_id = X AND is_lead = True` before the `UPDATE cases` call. If no lead row found (shouldn't happen but possible with data corruption), skip the write silently.
**Warning signs:** case_name updates appearing on non-lead cases in consolidated arguments.

### Pitfall 3: Not guarding metadata DB writes with dry_run
**What goes wrong:** Cover metadata is extracted and written to the DB even in `--dry-run` mode, which the operator uses to preview parse output without committing.
**Why it happens:** The `extract_cover_metadata()` call is pure computation so it naturally goes before the dry-run gate — but the DB writes must stay after the gate.
**How to avoid:** Structure `_run_parse_inner` so extraction (CPU) runs early, but all `session.execute(update(...))` calls are inside the post-dry-run code path.
**Warning signs:** `--dry-run` output shows "Cover metadata written" before the "Dry-run mode: ... NOT written to DB" message.

### Pitfall 4: Last-name collision in advocate side mapping
**What goes wrong:** Two advocates share the same last name in one argument. The dict key collision silently assigns the second advocate's side to both.
**Why it happens:** Using last name as the dict key.
**How to avoid:** Accept this as a known limitation for Phase 16 (per CONTEXT.md: unmatched participants stay UNKNOWN, partial updates accepted). Document in code.
**Warning signs:** Only occurs with arguments having two advocates sharing a last name — vanishingly rare.

### Pitfall 5: Multi-line "On behalf of" text in TOC
**What goes wrong:** For amicus advocates, the side line may wrap across multiple TOC lines:
```
GEN. DONALD B. VERRILLI, JR., ESQ.
For the United States, as amicus curiae,
supporting Petitioners on Question 1 28
```
`TOC_AMICUS_RE` must match on the continuation line (`supporting Petitioners on Question 1 28`) as well.
**How to avoid:** Keep `pending_name` set across multiple non-ESQ. lines, searching each for `amicus curiae`. Clear `pending_name` only when a match is found OR when a new ESQ. line begins.
**Warning signs:** `GEN. VERRILLI` stays `UNKNOWN` instead of mapping to `AMICUS`.

### Pitfall 6: Heritage "Date:" format uses no day-of-week prefix
**What goes wrong:** A regex requiring the day-of-week prefix (Monday/Tuesday/...) fails on Heritage cover page 0.
**Why it happens:** Heritage cover page has `Date: April 24, 2024` with no weekday prefix.
**How to avoid:** Use two separate patterns — `DATE_LINE_RE` (requires weekday) for pages 1+ and `HERITAGE_DATE_RE` (no weekday, has `Date:` prefix) for page 0. Or use a single pattern where the weekday prefix is optional. Scan all pages 0–2; return first match from either pattern.
**Warning signs:** Heritage transcripts consistently fail to extract `argued_date` while Alderson ones succeed.

---

## Code Examples

### Minimal extraction function skeleton

```python
# Source: validated against 9 PDFs in data/pdfs/ during research
from pathlib import Path
from datetime import date
import re
import pdfplumber
from pipeline.parser.extractor import strip_line_number

_MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

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

HEADER_RE = re.compile(
    r'^(?:Official|ALDERSON|Heritage|HERITAGE|Alderson|www\.|http|\(202\)|'
    r'\d{3,4}\s+L\s+Street|SUPREME\s+COURT)',
    re.IGNORECASE,
)
PAGE_NUM_RE = re.compile(r'^\d+$')


def _clean_lines(raw: str) -> list[str]:
    lines = []
    for l in raw.split("\n"):
        c = strip_line_number(l).strip()
        if c and not HEADER_RE.match(c) and not PAGE_NUM_RE.match(c):
            lines.append(c)
    return lines


def _parse_date(m: re.Match) -> date:
    return date(int(m.group(3)), _MONTH_MAP[m.group(1).lower()[:3]], int(m.group(2)))


def _extract_case_name(lines: list[str]) -> str | None:
    scotus_idx = next(
        (i for i, l in enumerate(lines) if 'SUPREME COURT OF THE UNITED STATES' in l.upper()),
        -1
    )
    if scotus_idx == -1:
        return None
    i = scotus_idx + 1
    while i < len(lines) and CAPTION_SEP_RE.match(lines[i]):
        i += 1
    name_parts = []
    for line in lines[i:]:
        if (re.match(r'^v\.?\s*[:).]', line, re.IGNORECASE)
                or re.match(r'^Petitioner', line, re.IGNORECASE)
                or CAPTION_SEP_RE.match(line)):
            break
        clean = CAPTION_PUNCT_RE.sub('', line).strip()
        if clean:
            name_parts.append(clean)
    return ' '.join(name_parts) if name_parts else None


def extract_cover_metadata(pdf_path: Path) -> dict:
    """Returns dict with 0-2 keys: 'argued_date' (date) and 'case_name' (str)."""
    result: dict = {}
    try:
        with pdfplumber.open(pdf_path) as pdf:
            raws = [pdf.pages[i].extract_text(layout=False) or ""
                    for i in range(min(3, len(pdf.pages)))]
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
        pass
    return result
```

### TOC side extraction skeleton

```python
# Source: validated against TOC pages from all 9 PDFs

TOC_ESQ_RE = re.compile(
    r'^(?:(?:GEN|MR|MS|MRS|DR)\.\s+)?[A-Z][A-Z\s.,]+,\s*ESQ(?:UIRE)?\.?\s*$',
    re.IGNORECASE,
)
TOC_SIDE_RE = re.compile(
    r'[Oo]n behalf of(?:\s+the)?\s+(Petitioner|Respondent|Petitioners|Respondents)',
    re.IGNORECASE,
)
TOC_AMICUS_RE = re.compile(r'amicus\s+curiae', re.IGNORECASE)


def _toc_last_name(line: str) -> str | None:
    line = re.sub(r'^(?:GEN|MR|MS|MRS|DR)\.\s+', '', line.strip(), flags=re.IGNORECASE)
    line = re.sub(r',\s*(?:JR|SR|III|II|IV)\.?,\s*ESQ(?:UIRE)?\.?\s*$', '', line, flags=re.IGNORECASE)
    line = re.sub(r',?\s*ESQ(?:UIRE)?\.?\s*$', '', line, flags=re.IGNORECASE)
    parts = line.strip().split()
    return parts[-1].rstrip(',').upper() if parts else None


def extract_advocate_sides(pdf_path: Path) -> dict[str, str]:
    """Returns {last_name_upper: SideEnum_value}. Returns {} on failure."""
    from api.models.models import SideEnum
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i in range(min(4, len(pdf.pages))):
                raw = pdf.pages[i].extract_text(layout=False) or ""
                if "C O N T E N T S" in raw:
                    lines = _clean_lines(raw)
                    mapping: dict[str, str] = {}
                    pending: str | None = None
                    for line in lines:
                        if TOC_ESQ_RE.match(line):
                            pending = _toc_last_name(line)
                            continue
                        if pending:
                            if TOC_AMICUS_RE.search(line):
                                mapping[pending] = SideEnum.AMICUS.value
                                pending = None
                            elif m := TOC_SIDE_RE.search(line):
                                role = m.group(1).upper()
                                mapping[pending] = (
                                    SideEnum.PETITIONER.value
                                    if role.startswith("PETITIONER")
                                    else SideEnum.RESPONDENT.value
                                )
                                pending = None
                    return mapping
    except Exception:
        pass
    return {}
```

### argument_participants bulk UPDATE skeleton

```python
# Source: direct read of pipeline/commands/parse.py step 7b pattern
# Matches existing update() call pattern in parse.py

from sqlalchemy import select, update
from api.models.models import ArgumentParticipant, SideEnum

async def _update_participant_sides(
    session: AsyncSession,
    argument_id: int,
    sides_map: dict[str, str],  # {last_name_upper: SideEnum_value}
) -> int:
    """
    Update argument_participants.side for advocates whose last name matches
    a key in sides_map. Returns count of rows updated.
    """
    if not sides_map:
        return 0

    result = await session.execute(
        select(ArgumentParticipant).where(
            ArgumentParticipant.argument_id == argument_id
        )
    )
    participants = result.scalars().all()

    updated = 0
    for p in participants:
        if p.raw_speaker_label is None:
            continue
        label_last = _normalize_label_last_name(p.raw_speaker_label)
        if label_last and label_last.upper() in sides_map:
            p.side = SideEnum(sides_map[label_last.upper()])
            updated += 1

    return updated


def _normalize_label_last_name(raw_label: str) -> str | None:
    """Extract last name component from 'MR. FRIEDMAN' -> 'FRIEDMAN'."""
    label = re.sub(
        r'^(?:MR|MS|MRS|GENERAL|GEN)\.\s+|^GENERAL\s+',
        '',
        raw_label.strip(),
        flags=re.IGNORECASE,
    )
    parts = label.strip().split()
    return parts[-1] if parts else None
```

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| Operator types case name/date manually via Phase 11 edit form | Parser pre-populates from PDF; operator reviews and corrects if needed | Phase 16 closes PARSE-01 |
| `argument_participants.side` stays `UNKNOWN` until operator assigns | Parser seeds initial sides from TOC; operator corrects edge cases via Phase 15 dropdown | Phase 16 closes PARSE-02 |

**No deprecated patterns in this phase** — Phase 16 extends, never replaces, the existing parse pipeline.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Last-name collision (two advocates with same last name in one argument) is rare enough to ignore for Phase 16 | Pattern 5 / Pitfall 4 | One advocate's side stays UNKNOWN when it should be mapped; operator fixes via Phase 15 dropdown — low risk |
| A2 | Alderson transcripts older than 2006 follow the same cover-page structure as the tested range (2006–2015) | Standard Stack | Older transcripts may have different date or case-name line formats; fail-safe design means extraction fails silently, operator enters values manually |
| A3 | The `C O N T E N T S` string (spaced letters) is unique to the TOC page and never appears in argument body pages | Pattern 5 | False positive would cause side detection to parse body text as TOC — unlikely since body pages have no such header |

**Three assumptions.** All are low-risk given the fail-safe design (D-05, D-09).

---

## Open Questions

1. **Where exactly in `_run_parse_inner` do the metadata DB writes go relative to the PipelineRun row creation?**
   - What we know: dry-run gate is at line 212–215; PipelineRun row is created at lines 222–231 (step 2d); utterance writes are steps 7/7b.
   - Recommendation: Write `argued_date` and `case_name` **after** PipelineRun row creation (step 2d) and **before** utterance writes (step 7). This keeps all writes inside the same session transaction. The `source_run.argument_id` is available from step 1 load.

2. **Should `extract_cover_metadata()` and `extract_advocate_sides()` be called before or inside the `async with get_session()` block?**
   - What we know: Both are pure synchronous pdfplumber I/O; DB session is async.
   - Recommendation: Call both **before** the `async with get_session() as session:` block (at the top of `_run_parse_inner` after the PDF path validation). Pass the result dicts into the session block. Eliminates any risk of blocking inside an async context.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 16 introduces no external dependencies. pdfplumber, SQLAlchemy async, and all required Python stdlib modules are already installed and in use by the existing pipeline.

---

## Validation Architecture

`workflow.nyquist_validation` is `false` in `.planning/config.json` — section omitted per config.

---

## Security Domain

This phase touches only the offline pipeline CLI (no HTTP endpoints, no user-facing features). ASVS categories V2–V4 do not apply.

| ASVS Category | Applies | Rationale |
|---------------|---------|-----------|
| V5 Input Validation | Minimal | PDF is operator-supplied from internal ingest; regex fails safely with no write |
| V6 Cryptography | No | No crypto operations |
| SQL injection | No | SQLAlchemy ORM parameterized queries; no string interpolation in SQL |

**No new security surface introduced.** Cover extraction reads immutable files; DB writes are parameterized ORM updates to existing columns.

---

## Sources

### Primary (HIGH confidence — verified against actual codebase + live PDFs)
- `pipeline/parser/extractor.py` — `extract_pages`, `strip_line_number`, `normalize_text` reusable utilities; page range confirmed
- `pipeline/commands/parse.py` — `_run_parse_inner` step sequence; `source_run.argument_id` availability; dry-run gate position; `update().execution_options(synchronize_session=False)` pattern
- `api/models/models.py` — `Argument.argued_date` (Date column); `Case.case_name`; `CaseArgument.is_lead`; `ArgumentParticipant.side` + `raw_speaker_label`; `SideEnum` values
- `data/pdfs/*.pdf` (9 PDFs) — actual cover page text extracted and regex patterns validated interactively

### Secondary (MEDIUM confidence — from project planning artifacts)
- `.planning/phases/16-parser-improvements/16-CONTEXT.md` — all locked decisions D-01 through D-09
- `.claude/skills/spike-findings-scotuschat/references/pdf-extraction.md` — validated extraction patterns from original spike

### Tertiary (LOW confidence)
- None. All claims verified against codebase or live PDFs.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; all dependencies confirmed present
- Architecture: HIGH — integration points verified by reading parse.py step-by-step
- Regex patterns: HIGH — tested interactively against 9 real PDF files
- Pitfalls: HIGH — all verified against actual PDF data

**Research date:** 2026-06-26
**Valid until:** Stable — no external dependencies; valid until PDF format changes
