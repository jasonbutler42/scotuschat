---
phase: 16-parser-improvements
plan: "02"
subsystem: pipeline
tags: [parser, side-detection, toc, advocate-sides, sqlalchemy, tdd]
status: complete

dependency_graph:
  requires:
    - pipeline/parser/cover_extractor.py (extract_advocate_sides, _toc_last_name, _parse_toc_sides — built in Plan 16-01)
    - pipeline/commands/parse.py (_run_parse_inner, extract_advocate_sides import — Plan 16-01)
    - api/models/models.py (ArgumentParticipant, SideEnum, argument_id)
  provides:
    - pipeline/tests/test_cover_extractor.py (8 new PARSE-02 unit tests — 21 total)
    - pipeline/commands/parse.py: _normalize_label_last_name, _update_participant_sides (module-level helpers)
    - pipeline/commands/parse.py: advocate_sides log print + _update_participant_sides call site after step 7b
  affects:
    - pipeline/commands/parse.py (helpers + wiring)

tech_stack:
  added: []
  patterns:
    - TDD RED/GREEN: tests added first, then module-level helpers, then call-site wiring
    - ORM attribute mutation for side UPDATE (p.side = SideEnum(value)) — relies on session flush/commit
    - D-08 partial update: only matching participants updated; unmatched stay UNKNOWN
    - D-09 silent-fail: extract_advocate_sides never raises; {} returned on any failure
    - Pitfall 3 guard: _update_participant_sides call after dry-run gate (line 236 in parse.py)
    - Post-step-7b placement: side UPDATE after argument_participants rows are seeded

key_files:
  created: []
  modified:
    - pipeline/tests/test_cover_extractor.py
    - pipeline/commands/parse.py

decisions:
  - "_normalize_label_last_name added to parse.py (not reused from cover_extractor.py) — keeps module self-contained; cover_extractor.py version remains for its own internal use"
  - "_update_participant_sides uses ORM attribute mutation (p.side = ...) matching existing participant-seeding pattern in step 7b, not bulk update() — consistent with how step 7b mutates ORM objects"
  - "Threat T-16-07 mitigated: _update_participant_sides call placed after step 7b flush (rows guaranteed) and guarded by run.argument_id is not None"
  - "Threat T-16-08 mitigated: call site is after dry-run gate line 236; extract_advocate_sides (CPU-only) runs before gate per Pitfall 1 requirement"

metrics:
  duration_minutes: 30
  completed_date: "2026-06-26"
  tasks_completed: 3
  files_changed: 2

requirements:
  - PARSE-02
---

# Phase 16 Plan 02: Advocate Side Detection Summary

**One-liner:** TOC-based advocate side detection wired into parse step — last-name matching maps PETITIONER/RESPONDENT/AMICUS from TOC ESQ. pairs to argument_participants.side after step 7b.

## What Was Built

Added PARSE-02 advocate side detection to the parse pipeline step:

1. **`pipeline/tests/test_cover_extractor.py`** (extended) — 8 new unit tests covering PARSE-02 behaviors:
   - `test_toc_last_name_simple`: `MARY L. BONAUTO, ESQ.` → `BONAUTO`
   - `test_toc_last_name_strips_gen_prefix_and_jr_suffix`: `GEN. DONALD B. VERRILLI, JR., ESQ.` → `VERRILLI`
   - `test_toc_last_name_no_prefix`: `SHAY DVORETZKY, ESQ.` → `DVORETZKY`
   - `test_toc_sides_petitioner_and_respondent`: standard TOC line pairs produce correct side mapping
   - `test_toc_sides_amicus_multiline`: `amicus curiae` on continuation line maps pending name to AMICUS (Pitfall 5)
   - `test_toc_sides_empty_on_no_recognizable_lines`: returns `{}` for unrecognized content (D-09)
   - `test_extract_advocate_sides_missing_pdf_returns_empty`: D-09 silent-fail
   - `test_extract_advocate_sides_returns_dict`: always returns dict, never None

2. **`pipeline/commands/parse.py`** (extended with module-level helpers):
   - `_normalize_label_last_name(raw_label) -> str | None`: strips `MR./MS./MRS./GEN./GENERAL` prefix, returns last whitespace-delimited token
   - `_update_participant_sides(session, argument_id, sides_map) -> int`: async helper; fetches all `ArgumentParticipant` rows for the argument, normalizes each `raw_speaker_label` to last name, matches against `sides_map`, sets `p.side = SideEnum(value)` via ORM attribute mutation; returns updated count

3. **`pipeline/commands/parse.py`** (wiring in `_run_parse_inner`):
   - Print `f"Advocate sides mapped: {advocate_sides}"` when non-empty (before session, after `extract_advocate_sides` call from Plan 16-01)
   - After step 7b participant-seeding flush and after PARSE-01 metadata UPDATE blocks: `if advocate_sides and run.argument_id is not None: sides_updated = await _update_participant_sides(session, run.argument_id, advocate_sides)`
   - Placement satisfies all key constraints: CPU extraction before session (Pitfall 1), DB write after dry-run gate (Pitfall 3), UPDATE after step 7b rows exist (T-16-07)

## Verification Results

All acceptance criteria passed:

- `grep -c "def extract_advocate_sides" pipeline/parser/cover_extractor.py` → 1 (Plan 16-01)
- `grep -c "def _toc_last_name" pipeline/parser/cover_extractor.py` → 1 (Plan 16-01)
- `grep -cE "TOC_ESQ_RE|TOC_SIDE_RE|TOC_AMICUS_RE" pipeline/parser/cover_extractor.py` → 3 (Plan 16-01)
- `python -c "from pipeline.parser.cover_extractor import extract_advocate_sides; print(extract_advocate_sides(Path('does-not-exist.pdf')))"` → `{}` (D-09 proven)
- `grep -c "def _update_participant_sides" pipeline/commands/parse.py` → 1
- `grep -c "def _normalize_label_last_name" pipeline/commands/parse.py` → 1
- `grep -c "from pipeline.parser.cover_extractor import" pipeline/commands/parse.py` → 1 (includes extract_advocate_sides)
- `grep -c "advocate_sides = extract_advocate_sides(pdf_path)" pipeline/commands/parse.py` → 1
- `grep -c "_update_participant_sides(session, run.argument_id, advocate_sides)" pipeline/commands/parse.py` → 1
- Line order: extract_advocate_sides (142) < dry-run gate (236) < Seeded print (306) < _update_participant_sides call (350) ✓
- `pytest pipeline/tests/test_cover_extractor.py -x -q` → 21 passed (13 PARSE-01 + 8 PARSE-02)
- `pytest pipeline/tests/test_parse.py -q` → 3 passed / 3 pre-existing failures (unchanged from Plan 16-01 baseline — deferred per scope boundary)

## Deviations from Plan

### Auto-fixed Issues

None — plan executed as written.

### Pre-existing Issues (Out of Scope)

The following 3 `test_parse.py` failures existed before Phase 16 and remain unchanged:
- `test_run_id_strategy` — `args.job_id` AttributeError (test Namespace missing `job_id`)
- `test_llm_failure_modes` — same AttributeError
- `test_section_hint_not_cascade` — section_hint assertion failure

Documented in `.planning/phases/16-parser-improvements/deferred-items.md` per Plan 16-01.

## Threat Mitigations Applied

| Threat | Mitigation Applied |
|--------|-------------------|
| T-16-05: DoS via malformed TOC | `try/except Exception: pass` in `extract_advocate_sides` (D-09) |
| T-16-06: Wrong side via last-name collision | Documented in `_update_participant_sides` docstring (Pitfall 4 known limitation) |
| T-16-07: Side UPDATE before participant rows exist | Call placed after step 7b seeding flush (line 303) + `run.argument_id is not None` guard |
| T-16-08: Side update during --dry-run | Call at line 350, after dry-run gate at line 236 |

## Known Stubs

None — all functionality is wired. When `advocate_sides` is empty (`{}`) or `run.argument_id` is None, the `_update_participant_sides` call is skipped cleanly and all participants remain `UNKNOWN`. The operator assigns via the Phase 15 advocate role dropdown.

## Threat Flags

No new security-relevant surface introduced. The TOC regex parsing uses no SQL string interpolation; `_update_participant_sides` uses ORM attribute mutation under the existing session transaction.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| pipeline/tests/test_cover_extractor.py | FOUND |
| pipeline/commands/parse.py | FOUND |
| Commit afed6bb (Task 1 — tests) | FOUND |
| Commit 2bad936 (Task 2 — helpers) | FOUND |
| Commit 8a7988c (Task 3 — wiring) | FOUND |
