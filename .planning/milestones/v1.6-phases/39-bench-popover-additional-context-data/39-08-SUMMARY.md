---
phase: 39-bench-popover-additional-context-data
plan: 08
subsystem: ui
tags: [svelte, svelte5-runes, sveltekit, popover, gap-closure, apolitical-framing]

# Dependency graph
requires:
  - phase: 39-bench-popover-additional-context-data
    plan: "05"
    provides: "Rebuilt SpeakerPopover.svelte header-row-plus-stacked-sections layout, which this plan restyles to match the mockups"
provides:
  - "Padded separator snippet ({#snippet separator(pad)}) so the birth/death and president/party dot glyph renders with real space instead of being trimmed by Svelte at {#if} block boundaries"
  - "Per-section hairline dividers on all four stacked sections below the header row (birth/death line, advocate descriptor, bio block, tenure list), each one riding along with its section when that section is omitted for missing data"
  - "Two-column tenure row pair matching the mockup: semibold office title left / right-aligned month-and-year range, then appointed_by+party left / reason_left right"
  - "formatMonthYear()/tenureRange() UTC-pinned date helpers for month-and-year tenure range granularity"
  - "api/tests/test_phase39_popover_ui_contract.py — 17-test DB-free source-contract module pinning all of the above plus a re-locked apolitical-rendering regression guard"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Svelte 5 {#snippet}/{@render} used for a reusable padded separator span — the fix for Svelte's known whitespace-trimming-at-{#if}-boundary behavior: moving the space into an element's own padding instead of a text node inside a conditional block body"
    - "Per-tenure-block leading margin via `margin-top:{i === 0 ? '0' : '8px'}` (indexed {#each}) instead of a trailing margin-bottom, so the last block never leaves dead space under it"
    - "Two-column row layout via display:flex;justify-content:space-between;align-items:baseline;gap:8px, with min-width:0 on the wrapping left cell and flex-shrink:0 + white-space:nowrap on the non-wrapping right cell"
    - "Pure-Python static source-contract test (ROOT + _source() + regex/substring assertions, no DB, no node subprocess) — the only automated verification available for a Svelte component in a repo with no frontend test framework, matching test_docket_ui_contract.py's established idiom"

key-files:
  created:
    - api/tests/test_phase39_popover_ui_contract.py
  modified:
    - app/src/lib/components/SpeakerPopover.svelte

key-decisions:
  - "Wrote the test module before touching the component (TDD RED first), confirming the RED run failed exactly the tests this plan's own acceptance criteria predicted (tests 1-4 and 10-14/16, 10 total) while tests 5-9/15/17 already passed as pre-existing regression guards"
  - "Kept the president/party separator's {@render separator(4)} change bundled into Task 1's commit (not deferred to Task 2), because Task 1's own action text calls for replacing both inline separators through the snippet, even though the two-column row rebuild itself is Task 2's job"
  - "Used _function_body() brace-balanced extraction in the test module to check formatMonthYear's body specifically for the absence of a day: component, rather than a whole-file substring search that would have been contaminated by formatShort's own day: 'numeric'"

requirements-completed: [PUB-04]

coverage:
  - id: G2
    description: "The separator between birth/death dates and between president/party renders with clear space on both sides instead of flush against adjacent text (39-UAT.md gap 2, test 12)"
    requirement: "PUB-04"
    verification:
      - kind: other
        ref: "api/tests/test_phase39_popover_ui_contract.py::test_separator_snippet_declared_and_glyph_appears_exactly_once, ::test_both_separators_rendered_through_snippet_with_explicit_padding, ::test_separator_snippet_applies_padding_argument_as_horizontal_padding"
        status: pass
    human_judgment: true
    rationale: "Source-contract tests pin the mechanism (padding on an element instead of trimmable text); genuine visual legibility confirmation is deferred to Plan 39-09's operator checkpoint, since this repo has no frontend test framework."
  - id: G3
    description: "Each tenure renders as a two-column row pair matching the mockup: semibold office title left with right-aligned date range, then appointed_by+party left with reason_left right (39-UAT.md gap 3, test 13)"
    requirement: "PUB-04"
    verification:
      - kind: other
        ref: "api/tests/test_phase39_popover_ui_contract.py::test_two_column_rows_exist, ::test_right_column_cannot_be_squeezed, ::test_office_title_is_only_promoted_element, ::test_dash_joined_single_line_is_gone"
        status: pass
    human_judgment: true
    rationale: "Layout and weight-discipline are pinned by source contract; genuine visual comparison against popover - Bench.png/popover-Advocate.png is deferred to Plan 39-09."
  - id: G3b
    description: "Tenure date ranges show month-and-year granularity, formatted timezone-independently"
    requirement: "PUB-04"
    verification:
      - kind: other
        ref: "api/tests/test_phase39_popover_ui_contract.py::test_format_month_year_is_utc_pinned_month_and_year_only, ::test_format_short_survives_for_birth_death_line"
        status: pass
    human_judgment: false
  - id: G-dividers
    description: "Every stacked section below the header row carries one hairline divider that is omitted along with its section when the section's data is missing"
    requirement: "PUB-04"
    verification:
      - kind: other
        ref: "api/tests/test_phase39_popover_ui_contract.py::test_every_section_below_header_carries_one_divider"
        status: pass
    human_judgment: false
  - id: G-nogap
    description: "The last tenure block leaves no dangling gap between it and the bottom of the card"
    requirement: "PUB-04"
    verification:
      - kind: other
        ref: "api/tests/test_phase39_popover_ui_contract.py::test_no_trailing_gap_after_last_tenure_block"
        status: pass
    human_judgment: false
  - id: D5-relocked
    description: "No visual property of any rendered value varies with which party or which reason it names — the new semibold weight applies to the office title only (re-locks 39-05's D5 as a durable test, ROADMAP criterion 3)"
    requirement: "PUB-04"
    verification:
      - kind: other
        ref: "api/tests/test_phase39_popover_ui_contract.py::test_apolitical_rendering_guard, ::test_apolitical_rendering_guard_after_restyle, ::test_office_title_is_only_promoted_element (exact font-weight:600 count == 4)"
        status: pass
    human_judgment: false
  - id: D-scale
    description: "The card still uses exactly four type sizes plus the pre-existing avatar-initials size, exactly two weights, and no colour outside the app.css token set"
    requirement: "PUB-04"
    verification:
      - kind: other
        ref: "api/tests/test_phase39_popover_ui_contract.py::test_type_scale_unchanged, ::test_color_set_unchanged"
        status: pass
    human_judgment: false

duration: ~35min
completed: 2026-07-28
status: complete
---

# Phase 39 Plan 08: Bench popover mockup-fidelity gap closure Summary

**Closed 39-UAT.md gaps 2 and 3 by moving the birth/death and president/party separator's space into a `{#snippet}` span (fixing Svelte's whitespace-trimming at `{#if}` block boundaries), giving all four stacked sections their own hairline divider, and rebuilding each tenure block into the mockup's two-column row pair with month-and-year date granularity — all pinned by a new 17-test DB-free source-contract module.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-07-28
- **Tasks:** 2 completed
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments

- Root-caused the illegible separator: Svelte trims whitespace-only text at the start/end of an `{#if}` block body, so the inline `" · "` text written inside the birth/death and president/party guards rendered flush against adjacent text. Fixed by declaring `{#snippet separator(pad: number)}<span style="padding:0 {pad}px;">·</span>{/snippet}` and rendering both separators through it (`{@render separator(8)}` for the wider birth/death gap, `{@render separator(4)}` for the tighter president/party gap) — the space now lives on an element's own padding, which Svelte cannot trim.
- Gave each of the four stacked sections below the header row (birth/death line, advocate descriptor, bio block, tenure list) its own `border-top:1px solid #334155;margin-top:16px;padding-top:16px;` leading chrome, so a section omitted for missing data (e.g. a living Justice with no bio, or an advocate with no tenure section) takes its divider with it automatically — no separate conditional logic needed.
- Added `formatMonthYear()` (UTC-pinned `Intl.DateTimeFormat` with `month: 'short'`/`year: 'numeric'`, no day component) and `tenureRange()` (joins the two endpoints with a spaced en dash, preserving the existing `?`/`present` fallbacks) beside the untouched `formatShort()`.
- Rebuilt each tenure block from three stacked unemphasised lines into the mockup's two-row layout: Row 1 is always rendered (office title left at 13px/600/`#e2e8f0`, date range right-aligned/non-wrapping at 13px/400/`#94a3b8`); Row 2 renders only when `appointed_by` or `reason_left` is non-null (president+party left, reason right, each cell independently omitted when its value is null).
- Replaced the per-block trailing `margin-bottom:16px` with a leading `margin-top:{i === 0 ? '0' : '8px'}` (indexed `{#each}`), closing the dead-space gap under the last tenure block.
- Weight discipline: the new semibold weight belongs to the office title only. Total `font-weight:600` count in the file is now exactly 4 (avatar initials, name, role pill, office title) — no date, president, party, or reason value carries any weight/colour/size difference from its siblings.

## Task Commits

Each task was committed atomically:

1. **Task 1: Give the separator real space, and separate every section with a rule** - `a8546df8` (test)
2. **Task 2: Rebuild each tenure as the mockup's two-column row pair** - `72da22a4` (feat)

## Files Created/Modified

- `api/tests/test_phase39_popover_ui_contract.py` (created) - 17-test pure-Python source-contract module (no DB, no `_db_configured` gate, no `node` subprocess) following `test_docket_ui_contract.py`'s `ROOT` + `_source()` idiom. Locks the separator snippet/render/padding, per-section dividers, spacing/type/colour scale, the two-column tenure layout, weight discipline (exact `font-weight:600` count), month-and-year date helpers, no-trailing-gap, and the apolitical-rendering regression guard (asserted twice, once per task's region).
- `app/src/lib/components/SpeakerPopover.svelte` (modified) - Added the `separator` snippet; converted both inline separators to `{@render separator(...)}` calls; added `border-top`/`margin-top`/`padding-top` chrome to the birth/death paragraph, advocate descriptor paragraph, bio wrapper div, and tenure list div; added `formatMonthYear()`/`tenureRange()`; rebuilt the per-tenure markup into the two-row flex layout described above.

## RED Run Results (per task, before editing)

**Task 1** (component in its pre-plan state): 10 of 17 tests failed —
`test_separator_snippet_declared_and_glyph_appears_exactly_once`,
`test_both_separators_rendered_through_snippet_with_explicit_padding`,
`test_separator_snippet_applies_padding_argument_as_horizontal_padding`,
`test_every_section_below_header_carries_one_divider` (Task 1's own tests 1-4), plus
`test_two_column_rows_exist`, `test_right_column_cannot_be_squeezed`,
`test_office_title_is_only_promoted_element`, `test_dash_joined_single_line_is_gone`,
`test_format_month_year_is_utc_pinned_month_and_year_only`,
`test_no_trailing_gap_after_last_tenure_block` (Task 2's tests 10-14, 16 — expected to still
fail since Task 2 hadn't run yet). The remaining 7 (tests 5-9, 15, 17 — spacing scale, type
scale, colour set, apolitical guard x2, `href=`/`Edit person` absence, `formatShort` survival)
already passed, confirming they were pre-existing regression guards over behaviour Plan 39-05
already got right.

**Task 2** (after Task 1's edits landed): the same 6 tests remained red until this task's edits
— `test_two_column_rows_exist`, `test_right_column_cannot_be_squeezed`,
`test_office_title_is_only_promoted_element`, `test_dash_joined_single_line_is_gone`,
`test_format_month_year_is_utc_pinned_month_and_year_only`,
`test_no_trailing_gap_after_last_tenure_block`. All 11 others (including Task 1's own 4) already
passed. After Task 2's edits: all 17 pass.

## Decisions Made

- Bundled the president/party separator's `{@render separator(4)}` replacement into Task 1's commit rather than Task 2's, since Task 1's own action text explicitly calls for replacing both inline separators through the snippet, even though the two-column tenure row rebuild itself is Task 2's job.
- The test module's `_function_body()` helper extracts `formatMonthYear`'s brace-balanced body specifically, rather than searching the whole file for the absence of `day:` — a whole-file search would have false-failed against `formatShort`'s own legitimate `day: 'numeric'`.

## Verification Results

- `./.venv/Scripts/python.exe -m pytest -k phase39_popover -q` → **17 passed, 0 skipped**.
- `./.venv/Scripts/python.exe -m pytest` (full suite) → **784 passed, 5 xfailed, 4 errors**. The 4 errors are the same pre-existing `test_phase38_people_ui_contract.py` node-driver Windows-path (`ENOENT`) failures documented since Phase 38/39 Plan 05 — this plan touches no Python files, so they are not a regression.
- `cd app && npm run check`:
  - Pre-task baseline: **0 errors, 36 warnings**.
  - After Task 1: **0 errors, 36 warnings** — unchanged.
  - After Task 2: **0 errors, 36 warnings** — unchanged.
- `grep -c 'border-top:1px solid #334155;' app/src/lib/components/SpeakerPopover.svelte` → 4.
- `grep -c '{@render separator(' …` → 2.
- Middle-dot glyph (`·`) count in the file → 1 (inside the snippet body only).
- `grep -oE '(margin|padding)-top: ?[0-9]+px' … | sort -u` → `margin-top:16px`, `margin-top:4px`, `padding-top:16px` — all on the declared 4/8/16/24px scale (the dynamic per-tenure-block `margin-top:{i === 0 ? '0' : '8px'}` is a Svelte expression, not a static literal, so it does not appear in this grep).
- `grep -c 'justify-content:space-between' …` → 2; `grep -c 'text-align:right' …` → 2.
- `grep -o 'font-weight:600' … | wc -l` → 4 (avatar initials, name, role pill, office title — pre-task count was 3).
- Deduplicated `font-size` set → `12px, 13px, 14px, 16px, 18px` (unchanged from Plan 39-05's baseline).
- Deduplicated `font-weight` set → `400, 600` (unchanged).
- Deduplicated hex-colour set → `#0f1117, #1e293b, #334155, #93c5fd, #94a3b8, #e2e8f0` — no colour outside the five app.css tokens plus the pre-existing `#0f1117` avatar-initials text colour.
- `grep -Eq 'Republican|Democratic|Federalist|Whig' …` → no match (both before and after Task 2).
- `grep -Ec 'N/A|Unknown|No bio' …` → 1 (the pre-existing source comment documenting the omission rule, confirmed still a comment, not rendered copy — unchanged from Plan 39-05's baseline).
- `grep -Ec 'href=|Edit person' …` → 0. No edit affordance was added (correctly deferred to backlog item 999.9, D-17).
- `grep -c '{@html' …` → 0 (T-39-28 mitigation intact).

## Plain-Language Before/After (for Plan 39-09's operator to check against the mockups)

**Separator, before:** the `·` between "b. Mar 19, 1891" and "d. Jul 9, 1974" (and between
"Dwight D. Eisenhower" and "Republican") rendered pressed flush against the text on both sides —
"1891·d." and "Eisenhower·Republican" — because Svelte trims whitespace-only text at the edges of
an `{#if}` block, silently eating the surrounding spaces.

**Separator, after:** the same small `·` glyph now sits inside its own padded span (8px of padding
on each side for the birth/death line, 4px for the president/party line), so it reads as
"1891 · d." and "Eisenhower · Republican" with clearly visible breathing room on both sides — the
glyph itself never changed size, only the space around it.

**Tenure rows, before:** each tenure rendered as three plain, unemphasised 13px lines stacked
directly on top of each other: `Chief Justice — 1953–1969`, then `Dwight D. Eisenhower ·
Republican`, then `Retired` — no visual hierarchy, no bold, no columns, and a year-only date range.

**Tenure rows, after:** each tenure now renders as two rows. Row 1 puts the office title
(`Chief Justice`) in semibold near-white on the left, with its date range (`Sep 1953 – Jun 1969`,
now month-and-year) right-aligned on the same line. Row 2 puts the appointing president and party
(`Dwight D. Eisenhower · Republican`) on the left, with the reason the tenure ended (`Retired`)
right-aligned on the same line beneath. Multiple tenure blocks sit close together (8px apart) with
no rule between them, matching the mockup, and the last block no longer leaves a trailing gap
before the card's bottom padding.

**Section dividers, before:** only the tenure list carried a top rule; the birth/death line, the
advocate descriptor, and the bio block had none, so the card read as one undifferentiated grey
block below the name/pill header.

**Section dividers, after:** every one of the four stacked sections below the header row now
carries its own hairline rule directly above it, and a section that's omitted for missing data
(e.g. no bio, or an advocate with no tenure section) takes its rule with it — no dangling or
doubled-up rules in any combination.

## Known Stubs

None introduced by this plan.

## Issues Encountered

None beyond the pre-existing `test_phase38_people_ui_contract.py` node-driver issue documented
above under Verification Results, which is out of this plan's scope (no Python changes, and
undisturbed since Plan 39-05/38-10).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Both 39-UAT.md gaps (2 and 3, tests 12/13) are closed and pinned by an automated regression
  test; a future edit to the separator spacing, the section dividers, or the tenure row layout
  will now fail `pytest -k phase39_popover` before it can regress silently.
- The apolitical-rendering constraint (ROADMAP criterion 3 / T-39-27) is now covered by a durable
  test — `test_office_title_is_only_promoted_element`'s exact `font-weight:600` count of 4 will
  fail if any future change adds emphasis to a party or reason value.
- Plan 39-09 owns the operator's visual re-confirmation against `popover - Bench.png` and
  `popover-Advocate.png`, plus the five deliberate mockup differences this plan's objective
  flagged for the operator (60px avatar, 24px card padding, `appointed_by` full-name rendering,
  the year-only-vs-month-year copywriting contract supersession, and the deferred "Edit person"
  link).
- No blockers. `npm run check` is clean (0 errors, 36 warnings, unchanged from baseline) and the
  full Python test suite shows no new failures.

---
*Phase: 39-bench-popover-additional-context-data*
*Completed: 2026-07-28*

## Self-Check: PASSED

- `app/src/lib/components/SpeakerPopover.svelte` — FOUND
- `api/tests/test_phase39_popover_ui_contract.py` — FOUND
- `.planning/phases/39-bench-popover-additional-context-data/39-08-SUMMARY.md` — FOUND
- Commit `a8546df8` — FOUND in `git log --oneline --all`
- Commit `72da22a4` — FOUND in `git log --oneline --all`
