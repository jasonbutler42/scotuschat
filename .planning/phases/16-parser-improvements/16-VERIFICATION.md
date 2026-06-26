---
phase: 16-parser-improvements
verified: 2026-06-26T00:00:00Z
status: passed
score: 10/10
behavior_unverified: 0
overrides_applied: 0
re_verification: null
---

# Phase 16: Parser Improvements — Verification Report

**Phase Goal:** Add cover-page metadata extraction (PARSE-01) and advocate side detection (PARSE-02) to the parse step, so operators see pre-populated argued_date, case_name, and advocate sides after parsing instead of entering them manually.
**Verified:** 2026-06-26
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | After parsing a standard SCOTUS transcript, the argument's argued_date is populated with the date extracted from the cover pages | VERIFIED | `extract_cover_metadata` searches pages 0–2 for `DATE_LINE_RE` / `HERITAGE_DATE_RE`; result written via `update(Argument).values(argued_date=...)` at parse.py:317 after dry-run gate |
| 2 | After parsing a standard SCOTUS transcript, the lead case's case_name is populated with the case name extracted from the cover pages | VERIFIED | `_extract_case_name` accumulates petitioner lines from caption page; result written via `update(Case).values(case_name=...)` at parse.py:335 guarded by `CaseArgument.is_lead == True` lookup |
| 3 | Parsing a transcript whose cover pages do not match known formats completes without error and leaves argued_date and case_name unchanged | VERIFIED | Both `extract_cover_metadata` and `extract_advocate_sides` wrap all logic in `try/except Exception: pass` (D-05/D-09); spotcheck confirmed `extract_cover_metadata(Path('does-not-exist.pdf'))` returns `{}` cleanly |
| 4 | Running parse in --dry-run mode extracts no metadata and makes no DB writes | VERIFIED | Dry-run gate at parse.py:236; `cover_meta` and `advocate_sides` extraction (lines 141–142) precede the gate (CPU-only); all UPDATE blocks (lines 315–350) are placed after the gate. Ordering confirmed: extraction (141, 142) < gate (236) < UPDATE blocks (315, 335, 350) |
| 5 | D-01: cover_extractor.py extraction is regex-only — no LLM call, no anthropic import; reads pages 0-2 currently skipped by extract_pages | VERIFIED | `cover_extractor.py` imports only `re`, `datetime.date`, `pathlib.Path`, `pdfplumber`, and three constants from `extractor.py`. No `anthropic` import anywhere in the file. Pages read via `range(min(3, len(pdf.pages)))` |
| 6 | After parsing a standard SCOTUS transcript, each advocate in argument_participants whose TOC appearance names a side has side set to PETITIONER/RESPONDENT/AMICUS instead of UNKNOWN | VERIFIED | `_parse_toc_sides` maps ESQ. lines to `SideEnum.PETITIONER/RESPONDENT/AMICUS.value`; `_update_participant_sides` applies via ORM mutation `p.side = SideEnum(value)` after step 7b flush (parse.py:350). Spotcheck confirmed petitioner/respondent/amicus mapping from synthetic TOC lines |
| 7 | Advocates with no matching TOC side entry remain UNKNOWN (partial update accepted) | VERIFIED | `_update_participant_sides` only mutates participants whose normalized last name matches a key in `sides_map`; unmatched loop iterations are no-ops (parse.py:427–433). D-08 behavior confirmed in test `test_toc_sides_empty_on_no_recognizable_lines` |
| 8 | Parsing a transcript whose TOC yields zero side mappings completes without error and leaves all participants UNKNOWN | VERIFIED | `_parse_toc_sides` returns `{}`; `_update_participant_sides` returns 0 immediately when `sides_map` is empty (parse.py:416–417); call site guards with `if advocate_sides and run.argument_id is not None` (parse.py:349) |
| 9 | D-06: side extraction reads only the TOC/appearances page (the C O N T E N T S page) | VERIFIED | `extract_advocate_sides` scans pages 0–3 and returns only when it finds a page containing `"C O N T E N T S"` literal; `_parse_toc_sides` processes only that page's cleaned lines |
| 10 | D-07: builds a raw_speaker_label -> SideEnum map then updates argument_participants.side; unmatched labels stay UNKNOWN | VERIFIED | `_parse_toc_sides` returns `{last_name_upper: SideEnum_value}`; `_update_participant_sides` fetches all participants, normalizes each `raw_speaker_label` via `_normalize_label_last_name`, applies only matching entries; confirmed by spotcheck of `_normalize_label_last_name` behavior |

**Score:** 10/10 truths verified (0 present-but-behavior-unverified)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pipeline/parser/cover_extractor.py` | New module with `extract_cover_metadata`, `extract_advocate_sides`, private helpers, regex constants | VERIFIED | File exists, 286 lines, all 8 expected functions present; imports `HEADER_RE`, `PAGE_NUM_RE`, `strip_line_number` from `extractor.py` (identity-verified in tests) |
| `pipeline/tests/test_cover_extractor.py` | Unit tests for cover-page helpers and TOC parsing | VERIFIED | File exists, 21 tests covering PARSE-01 (13) and PARSE-02 (8); all 21 pass in 0.17s |
| `pipeline/commands/parse.py` (modified) | Cover extraction wired into `_run_parse_inner`; two UPDATE blocks + side update call | VERIFIED | Imports verified; `cover_meta` and `advocate_sides` locals at lines 141–142; UPDATE blocks at lines 315–338; `_update_participant_sides` call at line 350 |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `_run_parse_inner` | `extract_cover_metadata` | Called at parse.py:141 before `async with get_session()` (line 148) | VERIFIED | Line 141 < line 148 — synchronous pdfplumber I/O never inside async DB transaction (Pitfall 1) |
| `_run_parse_inner` | `extract_advocate_sides` | Called at parse.py:142 before `async with get_session()` (line 148) | VERIFIED | Line 142 < line 148 — same Pitfall 1 guard |
| `cover_meta["argued_date"]` | `Argument.argued_date` | `update(Argument).where(Argument.id == source_run.argument_id)` at parse.py:317 | VERIFIED | UPDATE keyed by `source_run.argument_id`; after dry-run gate at line 236 |
| `cover_meta["case_name"]` | `Case.case_name` (lead only) | `select(CaseArgument.case_id).where(is_lead==True)` then `update(Case)` at parse.py:326–338 | VERIFIED | `CaseArgument.is_lead == True` guard prevents non-lead case overwrite (D-03, Pitfall 2) |
| `advocate_sides` | `argument_participants.side` | `_update_participant_sides` at parse.py:350 — after step 7b flush (line 305) | VERIFIED | Call at line 350 > Seeded print at line 306 — participant rows guaranteed to exist before UPDATE runs |
| `_run_parse_inner` dry-run gate | All DB writes | `if args.dry_run: return` at parse.py:236 | VERIFIED | All UPDATE and side-update calls are after line 236; extraction calls are before it |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `cover_extractor.py` | `result["argued_date"]` | `pdfplumber` regex scan of pages 0–2 via `DATE_LINE_RE` / `HERITAGE_DATE_RE` | Yes — extracted from PDF, not hardcoded | FLOWING |
| `cover_extractor.py` | `result["case_name"]` | `_extract_case_name` on cleaned lines from caption page | Yes — accumulated from PDF text lines | FLOWING |
| `cover_extractor.py` | `{last_name: SideEnum_value}` | `_parse_toc_sides` on TOC page lines matching `TOC_ESQ_RE` + `TOC_SIDE_RE` / `TOC_AMICUS_RE` | Yes — extracted from TOC page, not hardcoded | FLOWING |
| `parse.py` | `Argument.argued_date` | ORM `update(Argument).values(argued_date=cover_meta["argued_date"])` | Yes — real parameterized UPDATE to DB | FLOWING |
| `parse.py` | `Case.case_name` | ORM `update(Case).values(case_name=cover_meta["case_name"])` via `is_lead` guard | Yes — real parameterized UPDATE to DB | FLOWING |
| `parse.py` | `ArgumentParticipant.side` | ORM attribute mutation `p.side = SideEnum(value)` inside session | Yes — real ORM write flushed at end of session | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| D-05 silent-fail: missing PDF returns `{}` | `.venv/Scripts/python.exe -c "from pipeline.parser.cover_extractor import extract_cover_metadata; ..."` | `{}` | PASS |
| D-09 silent-fail: missing PDF returns `{}` for sides | `.venv/Scripts/python.exe -c "from pipeline.parser.cover_extractor import extract_advocate_sides; ..."` | `{}` | PASS |
| `_normalize_label_last_name` strips MR/MS/GEN/GENERAL | Inline Python assert on 4 cases | All assertions pass | PASS |
| `_toc_last_name` strips GEN prefix and JR suffix | Inline Python assert on 3 BONAUTO/VERRILLI/DVORETZKY cases | All assertions pass | PASS |
| `_parse_toc_sides` maps PETITIONER/RESPONDENT | Inline Python assert on standard TOC line pairs | `{DVORETZKY: PETITIONER, LIU: RESPONDENT}` | PASS |
| 21 unit tests pass | `.venv/Scripts/pytest.exe pipeline/tests/test_cover_extractor.py -x -q` | `21 passed in 0.17s` | PASS |
| `parse.py` syntax valid | `python -c "import ast; ast.parse(...)"` | `parse-ok` | PASS |
| `cover_extractor.py` syntax valid | `python -c "import ast; ast.parse(...)"` | `parse-ok` | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PARSE-01 | 16-01-PLAN.md | Parse step automatically extracts case name and argued date from transcript PDF and pre-populates argument metadata fields | SATISFIED | `extract_cover_metadata` extracts `argued_date` and `case_name`; wired into `_run_parse_inner` with UPDATE blocks after dry-run gate |
| PARSE-02 | 16-02-PLAN.md | Parse step automatically detects which side each advocate is arguing (petitioner/respondent/amicus) from the transcript structure and stores it as the initial per-argument role | SATISFIED | `extract_advocate_sides` extracts TOC side map; `_update_participant_sides` applies to `argument_participants.side` after step 7b |

**Note on ROADMAP SC-1 docket scope:** ROADMAP.md Phase 16 goal mentions "docket number" but REQUIREMENTS.md PARSE-01 explicitly states "docket number is already set at ingest; docket pre-population from the PDF is deferred to a future phase." Phase 16 CONTEXT.md marks docket extraction as explicitly out of scope. Docket is pre-populated at ingest (Phase 5/7); SC-1 is satisfied for the fields Phase 16 is responsible for.

**Note on ROADMAP SC-3 (editability):** Pre-populated fields being editable by the operator is satisfied by the existing Phase 11 argument edit UI (routes in `api/routers/admin.py`, service in `api/services/admin_arguments.py`). Phase 16 writes to standard writable columns — no new UI work required.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `pipeline/commands/parse.py` | 52–57 | Invisible unicode (UTF-8 em dash U+2014, en dash U+2013, soft hyphen U+00AD, right arrow U+2192) | INFO | Intentional — these are the exact byte literals used in `_normalize_dashes` string replacement logic. Not a debt marker or security concern. |

No TBD, FIXME, or XXX markers found in any Phase 16 modified files. No stub returns or placeholder components found.

---

### Human Verification Required

None. All must-haves are satisfied by code-level evidence and behavioral spot-checks. The parse step is an offline CLI tool with no visual/UI behavior to verify.

---

## Gaps Summary

No gaps. All 10 must-have truths are VERIFIED. Both PARSE-01 and PARSE-02 are fully implemented, wired, and tested. The 21-test suite passes. Dry-run safety, fail-safe contracts, and line-order constraints all verified.

---

_Verified: 2026-06-26_
_Verifier: Claude (gsd-verifier)_
