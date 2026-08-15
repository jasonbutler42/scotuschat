---
phase: 44-resolve-table-rework
plan: 02
subsystem: ui
tags: [sveltekit, svelte5, resolve-table, pure-source-contract]

# Dependency graph
requires:
  - phase: 44-01
    provides: "descriptor/descriptor_hint field names across ResolveRowUpdate, ResolveRow, ParticipantSideUpdate, SpeakerRow"
provides:
  - "ResolveCard.svelte five-column table (Raw Label, Resolved As, Bench/Advocate, Argument Role, Descriptor) with no Action column"
  - "rawLabelBadge and descriptorCell snippets"
  - "openPersonSearch — the single person-matching entry point (replaces handleConfirm/handleCorrect)"
  - "api/tests/test_phase44_resolve_table_contract.py pure static source contract (shared home for Plans 44-03/44-04)"
affects: [44-03, 44-04]

# Actuals (#2632)
actuals:
  tokens: 8800
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Svelte 5 {#snippet} extraction for repeated/always-rendered table-cell bodies (rawLabelBadge, descriptorCell), each independently unit-testable via brace-balanced source extraction in the pure-source contract test"
    - "Effect-seeded pre-filled combobox: rowMatchStates seeds correcting=true + disposition='confirmed' + comboQuery=candidate name for any row with a non-null auto_match_id, so an untouched pre-fill is indistinguishable (at submit time) from an operator-confirmed pick — no dedicated Confirm handler needed"

key-files:
  created:
    - api/tests/test_phase44_resolve_table_contract.py
  modified:
    - app/src/lib/components/ResolveCard.svelte

key-decisions:
  - "The 'Change' link (Resolved As, resolved-row state) only renders when `interactive && row.discrepancy` — i.e. only for a genuinely reviewable row during an active paused resolve session. A row resolved cleanly via the alias table (no discrepancy ever existed) or viewed in readonly mode gets personDisplay with no Change link, exactly matching the pre-Phase-44 Action column's behavior (it rendered '—' for `!row.discrepancy`). This avoids introducing a clickable-looking dead link for rows where clicking it would silently no-op (rowMatchStates has no entry for non-discrepancy rows)."
  - "openPersonSearch(row) takes the whole MergedRow (not just the label) so it can derive 'whatever name is currently displayed for the row' — row.full_name, falling back to row.discrepancy?.auto_match_name — and seed the combobox query from it. This lets 'Change' on an already-resolved row re-open the search pre-filled with the current name, matching the same pre-fill principle D-03/D-04 apply to the initial auto-match case."
  - "Kept the outer isPaused/discrepancy gating implicit in each branch's own condition (gated and correcting both bottom out on isPaused via needsSideGate/rowMatchStates) rather than re-adding an explicit `{#if isPaused && row.discrepancy}` wrapper, per the plan's literal 'rewrite as four states' instruction — verified this produces identical rendering to the pre-rework behavior for every row shape that exists in the current data model."

requirements-completed: [RESOLVE-01, RESOLVE-04]

coverage:
  - id: D1
    description: "Resolve table renders exactly five <th scope=\"col\"> headers (Raw Label, Resolved As, Bench/Advocate, Argument Role, Descriptor) in that order, with no Action column and no cell reading 'Action' anywhere"
    requirement: "RESOLVE-01"
    verification:
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_exactly_five_column_headers_declared"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_five_header_labels_appear_in_mockup_order"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_no_action_header_and_no_residual_title_header"
        status: pass
      - kind: other
        ref: "npm --prefix app run check (804 files, 0 errors)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every former Action-column person-matching action (select/change person) is reachable from inside the Resolved As cell; the collapsed entry point (openPersonSearch) is the sole handler, handleConfirm and the retired Confirm/Select button labels are gone"
    requirement: "RESOLVE-01"
    verification:
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_dedicated_confirm_handler_and_retired_button_labels_are_gone"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_open_person_search_is_the_one_entry_point"
        status: pass
    human_judgment: false
  - id: D3
    description: "An unresolved row with an auto-match candidate opens the person-search combobox already pre-filled with the candidate's name, the pre-filled option is badged 'Suggested' in the listbox, and an untouched pre-fill still counts as accepted on Continue Resolve submit (no Confirm button anywhere) — D-03/D-04"
    verification:
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_suggested_badge_lives_inside_the_listbox_option_region"
        status: pass
      - kind: other
        ref: "git diff shows allDispositioned/matchesJson derivation bodies unchanged — they already key off disposition!=null && personId!=null, which the seeding effect now satisfies for any candidate row"
        status: pass
    human_judgment: true
    rationale: "The pre-fill/badge is a visual affordance (seeded state + rendered markup verified structurally, but no browser render has been visually compared against resolve-speakers-panel.png yet). Deferred to Plan 44-04's checkpoint per this plan's own <verification> item 5 and logged to .planning/WINDOWS.md (id 2, kind unrun-verify) so it stays visible until that visual pass happens."
  - id: D4
    description: "A row still behind the pre-resolution side gate renders the Resolved As entry point as genuinely inert (aria-disabled, no click handler, no icon) rather than an active search link, and Descriptor renders on every row state (en dash for Bench, always-in-DOM input for editable rows, plain span for readonly) — RESOLVE-04, D-07, T-44-07"
    requirement: "RESOLVE-04"
    verification:
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_gated_entry_point_is_genuinely_inert"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_descriptor_cell_snippet_always_renders_bench_dash_and_editable_input"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_descriptor_input_carries_renamed_field_placeholder_and_truncation"
        status: pass
    human_judgment: false
  - id: D5
    description: "Every hex colour literal in the reworked file belongs to the UI-SPEC's nine-value approved palette — no new colour smuggled in by this pass"
    verification:
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_no_unapproved_hex_colors_introduced"
        status: pass
    human_judgment: false

duration: 21min
completed: 2026-08-01
status: complete
---

# Phase 44 Plan 02: Resolve Table Five-Column Structure & Collapsed Entry Point Summary

**`ResolveCard.svelte` restructured from six columns to five — the Action column is deleted, its two person-matching buttons fold into a single `openPersonSearch` entry point inside Resolved As with a D-04 pre-filled/accepted-by-default combobox, and Descriptor (renamed from Title in Plan 44-01) now always renders via a new `descriptorCell` snippet instead of disappearing for Bench/gated rows — locked by a new 11-test pure-source contract.**

## Performance

- **Duration:** 21 min
- **Started:** 2026-08-01T18:06:00Z (approx., per session read timestamps)
- **Completed:** 2026-08-01T18:19:47Z
- **Tasks:** 3
- **Files modified:** 2 (1 new: pure-source contract test; 1 modified: ResolveCard.svelte)

## Accomplishments

- **Five-column table skeleton (Task 1):** header row rewritten to exactly five `<th scope="col">` cells (Raw Label, Resolved As, Bench/Advocate, Argument Role, Descriptor) with uppercase/letter-spacing styling matching the mockup; the sixth Action header and its `<td>` are deleted entirely. The Raw Label cell is extracted into a new `rawLabelBadge` snippet (inline-block badge, `white-space: normal` so a pathologically long label wraps instead of hiding the discrepancy it exists to surface). The head comment documenting the locked column order is rewritten for Phase 44.
- **Descriptor always renders (Task 1, RESOLVE-04):** the Descriptor cell (renamed from Title in 44-01) is extracted into a new `descriptorCell` snippet with three unconditional branches — a static en dash for `side === 'BENCH'`, an always-in-DOM text input (Phase 27 CR-01/CR-02) with ellipsis-truncation and the "e.g. Attorney, Location, or Affiliation" placeholder for editable rows, and a plain span fallback for readonly rows. The cell body is never wrapped in an outer conditional that could suppress the whole `<td>`.
- **Collapsed Resolved As entry point (Task 2, D-03/D-04):** the `rowMatchStates` seeding `$effect` now seeds `correcting=true`, `disposition='confirmed'`, and `comboQuery` from `auto_match_name` for *any* row with a non-null `auto_match_id` (previously only rows flagged `auto_resolved`) — the combobox opens pre-filled from the start, and because `allDispositioned`/`matchesJson` already key off `disposition != null && personId != null` (both derivations left untouched), an untouched pre-fill flows into the Continue Resolve payload with zero Confirm-button code. Deleted the now-dead `handleConfirm` handler; renamed `handleCorrect` to `openPersonSearch(row)`, which additionally seeds the combobox query from whatever name is currently displayed for the row so re-opening search on an already-resolved row never starts empty.
- **Four-branch Resolved As cell (Task 2):** gated (inert `disabled`/`aria-disabled="true"` button, no icon, `clip-path: inset(50%)` sr-only explanation — the D-11/PJOB-18 gate survives losing its instructional sentence), correcting/pre-filled (existing combobox verbatim, plus a `Suggested` badge on the auto-matched `<li role="option">`), resolved (`personDisplay` + a `Change` text link, shown only when the row has a reviewable discrepancy), and unresolved-no-candidate (inline SVG magnifying-glass + "Select person…").
- **Pure-source contract (Task 3):** new `api/tests/test_phase44_resolve_table_contract.py` — 11 tests, zero DB gate, shared home for Plans 44-03/44-04's own sections. Locks the five-header order, the retired Action/Title absence, the Descriptor snippet's always-both-branches contract, `handleConfirm`'s absence, `openPersonSearch`'s ≥3 occurrences, the `Suggested` badge's location inside the `<li role="option">` region, the gated entry point's `aria-disabled`/sr-only pair, and — as a standing guard for every future pass — that every hex colour literal in the file belongs to the UI-SPEC's nine-value approved palette (verified to genuinely fail when an unapproved colour is injected, then reverted clean).

## Task Commits

Each task was committed atomically:

1. **Task 1: Five-column skeleton — headers, Raw Label badge, no Action column, always-present Descriptor cell** - `df322db1` (feat)
2. **Task 2: Collapse Confirm/Select/Change into one person-search entry point inside Resolved As** - `6b865abf` (feat)
3. **Task 3: Source-contract test for the five-column structure and the collapsed entry point** - `32bc550d` (test)

## Files Created/Modified

- `app/src/lib/components/ResolveCard.svelte` - five-column table, `rawLabelBadge`/`descriptorCell` snippets, `openPersonSearch` (replaces `handleConfirm`/`handleCorrect`), rewritten four-branch Resolved As cell
- `api/tests/test_phase44_resolve_table_contract.py` - new pure-source contract, 11 tests, shared home for 44-03/44-04

## Decisions Made

- See `key-decisions` in frontmatter: the `Change` link's `row.discrepancy`-gating (matches pre-Phase-44 Action-column behavior for non-discrepancy rows), `openPersonSearch`'s row-based pre-fill-from-current-display-name design, and the choice to keep isPaused/discrepancy gating implicit per-branch rather than re-introducing an outer wrapper.

## Deviations from Plan

None beyond the design choices already called out above as `key-decisions` — those were resolved within Claude's-Discretion latitude the plan explicitly grants for combobox/entry-point mechanics (CONTEXT.md), not treated as deviations requiring a rule citation.

## Issues Encountered

- **Literal-substring acceptance check for `>Change<`:** the plan's acceptance criteria require the literal substring `>Change<` to appear exactly once. My first draft put the button's text content on its own line (matching the pre-existing code style for the old Confirm/Select/Change buttons), which put whitespace between the tag's closing `>` and the word — failing the literal grep. Fixed by collapsing that one button's closing tag onto the same line as its text (`>Change</button>`), verified via `grep -c '>Change<'` returning 1.
- **Full-suite pytest invocation quirk (pre-existing, documented in 44-01's `deferred-items.md`):** running `./.venv/Scripts/python.exe -m pytest api/tests -q` directly (the plan's literal verification command) reproduces the same pre-existing failures 44-01 already diagnosed and deferred — `tests/conftest.py`'s `TEST_DATABASE_URL` redirect isn't triggered when `tests/` isn't an ancestor of the invoked paths, so unrelated tests (`test_admin_dev_routes.py`, `test_speakers_service.py`) collide with the real dev DB, and `test_phase38_people_ui_contract.py`'s Node-subprocess fixture path bug still errors. Re-ran with the corrected invocation `pytest tests/conftest.py api/tests -q`: **553 passed, 4 pre-existing errors (same file, same root cause), 0 failed** — exactly 44-01's baseline of 542 passed plus this plan's 11 new tests, confirming zero regressions. Not re-documented as a new deferred item since it's identical to the one 44-01 already logged; this plan's own `test_phase44_resolve_table_contract.py` and `test_phase44_descriptor_rename.py` both pass cleanly in isolation (17 passed, no DB gate needed).

## Known Stubs

None. All Descriptor/Raw-Label/Resolved-As states render real data — no hardcoded empty values, no placeholder-only components.

## Threat Flags

None. This plan's edits (markup restructuring, a client-side effect-seeding change, and a renamed handler) don't introduce new network endpoints, auth paths, or schema changes at a trust boundary — the existing per-row hidden-form submit path and the `?/resolve` batch action are unchanged, and Threats T-44-07/T-44-08/T-44-09/T-44-10 from the plan's own threat model are the complete relevant register (all `mitigate`/`accept`, none newly introduced).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 44-03 can proceed: the five-column structure and `descriptorCell`/`rawLabelBadge` snippets are stable, and Plan 44-03's own scope (segmented Bench/Advocate toggle, real writable Argument Role dropdown) touches the Bench/Advocate and Argument Role `<td>` bodies this plan deliberately left untouched.
- Plan 44-04 can proceed: the "Imported:" hint rework (`CopyableExtractedValue` prefix-label prop) and the final visual sign-off against `resolve-speakers-panel.png` are both still pending — the latter is explicitly this plan's own deferred item (`.planning/WINDOWS.md` id 2).
- No blockers. The full-suite pytest invocation quirk is pre-existing (documented in 44-01) and confirmed unrelated to this plan's changes via the corrected invocation.

---
*Phase: 44-resolve-table-rework*
*Completed: 2026-08-01*

## Self-Check: PASSED

- FOUND: `api/tests/test_phase44_resolve_table_contract.py`
- FOUND: `app/src/lib/components/ResolveCard.svelte`
- FOUND: commit `df322db1` (Task 1)
- FOUND: commit `6b865abf` (Task 2)
- FOUND: commit `32bc550d` (Task 3)
