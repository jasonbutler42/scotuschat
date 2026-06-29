---
phase: 16-parser-improvements
plan: "01"
subsystem: pipeline
tags: [parser, cover-extractor, regex, metadata, pdf, sqlalchemy]
status: complete

dependency_graph:
  requires:
    - pipeline/parser/extractor.py (HEADER_RE, PAGE_NUM_RE, strip_line_number)
    - api/models/models.py (Argument, Case, CaseArgument, SideEnum)
    - pipeline/commands/parse.py (_run_parse_inner, get_session)
  provides:
    - pipeline/parser/cover_extractor.py (extract_cover_metadata, extract_advocate_sides)
    - pipeline/tests/test_cover_extractor.py (13 unit tests)
    - parse.py: cover_meta + advocate_sides locals wired into _run_parse_inner
    - parse.py: argued_date UPDATE on Argument row after dry-run gate
    - parse.py: case_name UPDATE on lead Case row via CaseArgument.is_lead guard
  affects:
    - pipeline/commands/parse.py (imports, _run_parse_inner structure)

tech_stack:
  added: []
  patterns:
    - pdfplumber context manager open (pages 0-2 read independently of extract_pages)
    - D-05/D-09 fail-safe: try/except Exception: pass returning {} on all public functions
    - SQLAlchemy async update().execution_options(synchronize_session=False) for cover metadata
    - Pre-session pdf_path hoisting: brief pre-session read before main async session (Pitfall 1 guard)
    - is_lead guard: select(CaseArgument.case_id).where(is_lead==True) before case_name UPDATE

key_files:
  created:
    - pipeline/parser/cover_extractor.py
    - pipeline/tests/test_cover_extractor.py
  modified:
    - pipeline/commands/parse.py

decisions:
  - "New module cover_extractor.py (not extending extractor.py): separates cover-page concern; extractor.py unchanged"
  - "HEADER_RE, PAGE_NUM_RE, strip_line_number imported from extractor.py; not redefined"
  - "pdf_path resolution hoisted before main async with get_session() block via a brief pre-session read (Pitfall 1 guard)"
  - "extract_cover_metadata and extract_advocate_sides both called before the main session — synchronous pdfplumber I/O never inside async DB transaction"
  - "cover_meta and advocate_sides declared as locals before the main session; in scope at dry-run gate and post-flush region"
  - "Both UPDATE blocks placed after dry-run gate (line 234); extraction CPU-only portion runs before gate (Pitfall 3)"
  - "case_name write guarded by CaseArgument.is_lead == True select before UPDATE (D-03/Pitfall 2); skips silently if no lead row"
  - "D-04 always-overwrite: no write-if-blank conditional on either UPDATE block"

metrics:
  duration_minutes: 35
  completed_date: "2026-06-26"
  tasks_completed: 3
  files_changed: 3

requirements:
  - PARSE-01
---

# Phase 16 Plan 01: Cover-Page Metadata Extraction Summary

**One-liner:** Regex-only cover-page extraction (argued_date + case_name) wired into parse step with dry-run gate, is_lead guard, and D-05 fail-safe.

## What Was Built

Added PARSE-01 cover-page metadata extraction to the parse pipeline step:

1. **`pipeline/parser/cover_extractor.py`** (new) — Public functions `extract_cover_metadata(pdf_path)` and `extract_advocate_sides(pdf_path)`, plus private helpers `_clean_lines`, `_parse_date`, `_extract_case_name`, `_toc_last_name`, `_normalize_label_last_name`, `_parse_toc_sides`. Regex constants `DATE_LINE_RE`, `HERITAGE_DATE_RE`, `CAPTION_SEP_RE`, `CAPTION_PUNCT_RE`, `TOC_ESQ_RE`, `TOC_SIDE_RE`, `TOC_AMICUS_RE`, `_MONTH_MAP`. Reuses `HEADER_RE`, `PAGE_NUM_RE`, `strip_line_number` from `extractor.py`.

2. **`pipeline/tests/test_cover_extractor.py`** (new) — 13 unit tests covering `_extract_case_name` (Alderson format, no header → None, stops at v., multi-line), `_parse_date` (weekday and Heritage formats, case-insensitive), `_clean_lines` (drops headers, bare page numbers, strips line numbers), `extract_cover_metadata` (D-05 missing PDF → {}, always returns dict), and identity check that `HEADER_RE`/`PAGE_NUM_RE` are imported not redefined.

3. **`pipeline/commands/parse.py`** (modified) — Three additions:
   - Import block: added `Argument`, `Case`, `CaseArgument`; added `extract_cover_metadata`, `extract_advocate_sides`
   - Extraction call: hoisted pdf_path resolution before the main `async with get_session()` block via a brief pre-session read; `extract_cover_metadata(pdf_path)` and `extract_advocate_sides(pdf_path)` called synchronously before the async DB session (Pitfall 1 guard)
   - UPDATE blocks: Block A writes `argued_date` to the `Argument` row; Block B selects `CaseArgument.case_id WHERE is_lead==True` then writes `case_name` to the lead `Case` row — both after the dry-run gate, both using `synchronize_session=False`

## Verification Results

All acceptance criteria passed:

- `pytest pipeline/tests/test_cover_extractor.py -x -q` → 13 passed
- D-05 silent-fail: `extract_cover_metadata(Path('does-not-exist.pdf'))` → `{}`
- `HEADER_RE`, `PAGE_NUM_RE`, `strip_line_number` imported from extractor.py (not redefined)
- `def extract_cover_metadata` count = 1
- `update(Argument)` count = 1, `update(Case)` count = 1
- `CaseArgument.is_lead == True` count = 1
- `synchronize_session=False` count increased from 3 to 5 (+2 for new UPDATEs)
- Both UPDATE blocks at lines 315/333, after dry-run gate at line 234

## Deviations from Plan

### Auto-fixed Issues

None — plan executed as written.

### Out-of-Scope Issues Deferred

**Pre-existing test failures in `test_parse.py`** (Rule: out-of-scope per scope boundary):
- `test_run_id_strategy` — `args.job_id` attribute missing from test Namespace; pre-existing
- `test_llm_failure_modes` — same AttributeError (also pre-existing)
- `test_section_hint_not_cascade` — section_hint assertion failure (pre-existing)

All three failures existed before Phase 16 changes (confirmed via `git stash` check). Documented in `.planning/phases/16-parser-improvements/deferred-items.md`.

## Threat Mitigations Applied

All T-16-* threats from the plan's threat model were mitigated:

| Threat | Mitigation Applied |
|--------|-------------------|
| T-16-01: DoS via malformed PDF | `try/except Exception: pass` in `extract_cover_metadata` (D-05) |
| T-16-02: Wrong-row UPDATE | `argued_date` keyed by `source_run.argument_id`; `case_name` guarded by `CaseArgument.is_lead == True` |
| T-16-03: SQL injection via case_name | SQLAlchemy `update().values()` bound parameters — no string interpolation |
| T-16-04: DB write during --dry-run | Both UPDATE blocks after line 234 dry-run gate |

## Known Stubs

None — all functionality is wired. `cover_meta` and `advocate_sides` are populated from the PDF on every parse run. When extraction fails, empty dicts are returned and no writes are issued (the operator enters values manually via Phase 11 edit UI).

## Self-Check: PASSED

| Item | Status |
|------|--------|
| pipeline/parser/cover_extractor.py | FOUND |
| pipeline/tests/test_cover_extractor.py | FOUND |
| pipeline/commands/parse.py | FOUND |
| Commit da63b6a (Task 1) | FOUND |
| Commit ecca2f3 (Task 2) | FOUND |
| Commit 71fb6b4 (Task 3) | FOUND |
