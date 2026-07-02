---
phase: 22-schema-foundations
plan: "03"
subsystem: pipeline/parser
tags: [pipeline, toc-extraction, title, pjob-13, tdd]
status: complete
completed: "2026-07-02"
duration: "~22 minutes"
tasks_completed: 2
files_modified: 2
files_created: 0

dependency_graph:
  requires:
    - 22-02 (migration 0013 added argument_participants.title column)
  provides:
    - _parse_toc_titles in cover_extractor.py
    - extract_toc_data shared TOC-read entry point
    - _update_participant_titles in parse.py
    - advocate title writes to argument_participants.title on new parse runs
  affects:
    - pipeline/commands/parse.py (single PDF open for both sides and titles)

tech_stack:
  added: []
  patterns:
    - TDD RED/GREEN cycle (8 new tests)
    - Shared TOC read (D-12) — single pdfplumber.open for both sides and titles
    - Fail-safe extractor pattern (D-11) — try/except returns empty maps, never raises
    - Plain string assignment for title (no enum cast)

key_files:
  created: []
  modified:
    - pipeline/parser/cover_extractor.py
    - pipeline/commands/parse.py
    - pipeline/tests/test_cover_extractor.py

decisions:
  - "_parse_toc_titles loop: when pending_name set and next line is side/amicus, clear pending_name without recording (D-10 — subtitle must sit between name and side attribution)"
  - "extract_toc_data opens PDF once and calls both _parse_toc_sides and _parse_toc_titles on the same _clean_lines result (D-12)"
  - "extract_advocate_sides retained unchanged for backward compatibility (not deleted)"
  - "p.title assigned as plain string — no SideEnum or other enum cast around the value"

metrics:
  duration: "~22 minutes"
  completed: "2026-07-02"
  tasks: 2
  files: 3
---

# Phase 22 Plan 03: TOC Title Extraction — Summary

**One-liner:** TDD implementation of `_parse_toc_titles` + `extract_toc_data` in cover_extractor.py, and `_update_participant_titles` wired into parse.py via a single shared PDF open (D-12).

## What Was Built

### Task 1 (TDD): _parse_toc_titles and extract_toc_data in cover_extractor.py

**RED:** 8 new failing tests added to `pipeline/tests/test_cover_extractor.py`:
- Test 9 — `_parse_toc_titles`: subtitle capture, no-subtitle (side follows name), no-subtitle (amicus follows name), empty input, no ESQ lines, multiple advocates
- Test 10 — `extract_toc_data`: fail-safe on missing PDF, dict shape with sides+titles keys

**GREEN:** Two functions added to `pipeline/parser/cover_extractor.py`:

1. `_parse_toc_titles(lines: list[str]) -> dict[str, str]` — same loop skeleton as `_parse_toc_sides`. When `pending_name` is set and the next line is a side or amicus line, clears `pending_name` without recording (no subtitle present). Otherwise treats the next line as the subtitle string. Returns `{last_name_upper: subtitle}`.

2. `extract_toc_data(pdf_path: Path) -> dict` — opens the PDF once, scans pages 0–3 for `C O N T E N T S`, computes `_clean_lines(raw)` once, and returns `{"sides": _parse_toc_sides(lines), "titles": _parse_toc_titles(lines)}`. Wrapped in `try/except Exception: pass` — returns `{"sides": {}, "titles": {}}` on any failure.

`extract_advocate_sides` was kept in place (not deleted) for backward compatibility.

All 34 tests pass (26 pre-existing + 8 new).

### Task 2: Wire title extraction into parse.py

Changes to `pipeline/commands/parse.py`:
1. Import updated: `extract_advocate_sides` → `extract_toc_data`
2. CPU-side extraction block: single `toc = extract_toc_data(pdf_path)` call replaces separate `extract_advocate_sides(pdf_path)` call; unpacks `advocate_sides = toc["sides"]` and `advocate_titles = toc["titles"]`
3. `async def _update_participant_titles(session, argument_id, titles_map)` added after `_update_participant_sides`: same select/loop structure; assigns `p.title = titles_map[label_last.upper()]` as a plain string
4. Call site added after the sides update block: `if advocate_titles and run.argument_id is not None: titles_updated = await _update_participant_titles(...)`

## Verification

- `python -m pytest pipeline/tests/test_cover_extractor.py -q` → 34 passed, 0 failures
- `_parse_toc_titles` and `extract_toc_data` exist in cover_extractor.py; `extract_advocate_sides` still exists
- `_parse_toc_titles(['MARY L. BONAUTO, ESQ.', '  Solicitor General', 'On behalf of the Petitioner 3'])` → `{'BONAUTO': 'Solicitor General'}`
- `_parse_toc_titles([])` → `{}`
- `extract_toc_data(Path('nonexistent.pdf'))` → `{'sides': {}, 'titles': {}}` (no raise)
- `_update_participant_titles` defined in parse.py; `extract_toc_data` imported and called; `p.title` assigned as plain string
- `ast.parse(open('pipeline/commands/parse.py').read())` → exits 0

## Commits

| Hash | Message |
|------|---------|
| 971f4016 | test(22-03): add failing tests for _parse_toc_titles and extract_toc_data (RED) |
| 17e3911a | feat(22-03): add _parse_toc_titles and extract_toc_data to cover_extractor (GREEN) |
| d9522bc7 | feat(22-03): wire title extraction into parse step (PJOB-13) |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. The title mapping is fully wired end-to-end: PDF TOC → `_parse_toc_titles` → `extract_toc_data` → `advocate_titles` → `_update_participant_titles` → `argument_participants.title`. NULL title means no subtitle was found in the TOC; the operator fills via Phase 23 UI later (by design, D-11).

## Threat Surface

No new threat surface beyond what was documented in the plan's threat model. T-22-07 (malformed PDF DoS) is mitigated by the `try/except` in `extract_toc_data`. T-22-08 (title length) and T-22-09 (information disclosure) are accepted per the plan.

## Self-Check: PASSED

- `pipeline/parser/cover_extractor.py` — modified in-place, contains `_parse_toc_titles` and `extract_toc_data`
- `pipeline/commands/parse.py` — modified in-place, contains `_update_participant_titles`
- `pipeline/tests/test_cover_extractor.py` — modified in-place, 34 tests pass
- Commits 971f4016, 17e3911a, d9522bc7 confirmed in git log
