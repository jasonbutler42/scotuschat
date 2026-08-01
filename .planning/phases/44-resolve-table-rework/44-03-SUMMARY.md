---
phase: 44-resolve-table-rework
plan: 03
subsystem: ui
tags: [sveltekit, svelte5, resolve-table, segmented-toggle, pydantic-enum]

# Dependency graph
requires:
  - phase: 44-02
    provides: "ResolveCard.svelte five-column table (Raw Label, Resolved As, Bench/Advocate, Argument Role, Descriptor) with no Action column; descriptorCell/rawLabelBadge snippets"
provides:
  - "sideToggle snippet — a two-segment Bench/Advocate pill, exactly one active segment (or neither, in the D-07 gate state), also carrying the pre-resolution side gate"
  - "toggleSide(row, choice) — the toggle's click handler, with an early no-op return on the already-active segment"
  - "argumentRoleCell snippet — RESOLVE-06 lock affordance for resolved bench rows, preserved missing-tenure warning, RESOLVE-03 four-option writable dropdown for advocate/gated rows"
  - "chooseArgumentRole(row, value) — the dropdown's onchange handler; also satisfies the side gate when a role is picked before Bench/Advocate is chosen"
  - "A single always-present hidden <input name=\"side\"> per row — the sole submitting element for side; both visual controls are pure state mutators"
  - "flushSync() call inside submitRow — forces pending $state writes into the DOM before requestSubmit() serializes the form"
  - "api/tests/test_phase44_resolve_table_contract.py extended to 24 tests (RESOLVE-02/03/06 sections)"
  - "api/tests/test_phase44_argument_role_roundtrip.py — schema enum-boundary proof + DB-gated write-then-read round trip"
affects: [44-04]

# Actuals (#2632)
actuals:
  tokens: 7615
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "flushSync() from 'svelte' called as the first statement of a submit function, before requestSubmit() — closes the Svelte 5 $state-write-batched-into-a-microtask gap for any future per-row hidden-form submit that sets $state and submits synchronously in the same handler"
    - "Segmented two-button toggle absorbing a prior two-state gate: one component renders the resolved state (exactly one segment active) and the gate state (neither active) by deriving both from the same effectiveSide()/needsSideGate() functions, rather than a visually distinct gate control"
    - "Single hidden-input-as-sole-submitter for a value with two visual mutator controls (toggle + select): both controls carry no name/form attribute and only write to shared $state; one always-present hidden input reads that $state and is the only thing the form actually submits"

key-files:
  created:
    - api/tests/test_phase44_argument_role_roundtrip.py
  modified:
    - app/src/lib/components/ResolveCard.svelte
    - api/tests/test_phase44_resolve_table_contract.py

key-decisions:
  - "toggleSide's already-active check runs before the gated check — an early return with no state write and no submit happens regardless of gate state, so a second click on an active segment is always inert, not just when ungated (matches the plan's literal ordering: no-op check first, then gate check, then onSideChange)."
  - "argumentRoleCell's four branches are checked purely on side/missing_tenure/rowEditable, not on the gated flag — a gated row with side already BENCH (a currently-unreachable combination in this codebase, since parse seeds new participants at UNKNOWN) would still get the locked/missing-tenure treatment rather than the dropdown, matching the plan's literal branch order rather than special-casing gated rows into the dropdown branch unconditionally."
  - "SIDE_LABEL.PETITIONER/RESPONDENT/AMICUS reused for the dropdown's three real option labels (plan's explicit instruction) rather than retyping the strings, so the UI can never drift from api/services/speakers.py's ADVOCATE_LABEL_MAP without both breaking in the same commit."

requirements-completed: [RESOLVE-02, RESOLVE-03, RESOLVE-06]

coverage:
  - id: D1
    description: "The side <select> is gone; a two-segment pill (sideToggle) sets Bench versus Advocate with exactly one active segment, and neither active in the D-07 gate state; a single always-present hidden input is the sole element submitting the side form field"
    requirement: "RESOLVE-02"
    verification:
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_side_form_field_is_singular_and_lives_in_hidden_form"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_side_toggle_snippet_has_two_pressed_segments_and_one_group"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_flush_sync_imported_and_called_inside_submit_row"
        status: pass
      - kind: other
        ref: "npm --prefix app run check (804 files, 0 errors, 36 pre-existing warnings)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Clicking the already-active segment is a no-op (no state write, no submit) — toggleSide returns early; confirmSide/onSideChange are preserved unchanged, not replaced"
    requirement: "RESOLVE-02"
    verification:
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_toggle_side_handler_has_early_no_op_return"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_confirm_side_and_on_side_change_preserved_not_replaced"
        status: pass
    human_judgment: true
    rationale: "The early-return no-op is proven structurally (the handler contains a `return;` before any state write path), but the actual runtime behavior — clicking an already-active Advocate segment truly does not reset a stored PETITIONER to UNKNOWN in the browser — is a live-interaction check deferred to Plan 44-04's visual checkpoint, per this plan's own <verification> item 6."
  - id: D3
    description: "An advocate row offers four real Argument Role options (UNKNOWN/\"Select case role\" placeholder, Petitioner's Counsel, Respondent's Counsel, Amicus Curiae) in that order; the select carries no name/form attribute; the placeholder value is literally UNKNOWN, never an empty string or disabled option; choosing a role round-trips through the database for all three real roles"
    requirement: "RESOLVE-03"
    verification:
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_argument_role_select_is_singular_and_carries_no_name_or_form"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_argument_role_options_in_locked_order"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_argument_role_placeholder_is_real_unknown_value"
        status: pass
      - kind: integration
        ref: "api/tests/test_phase44_argument_role_roundtrip.py#test_argument_role_round_trips_for_each_real_advocate_role (DB-gated, verified against live scotus_test DB — all 3 parametrizations pass)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Out-of-enum side values are rejected server-side by Pydantic before reaching the ORM, proven by test (T-44-03) — the dropdown's option list is a UI convenience, never the enforcement boundary"
    requirement: "RESOLVE-03"
    verification:
      - kind: unit
        ref: "api/tests/test_phase44_argument_role_roundtrip.py#test_resolve_row_update_rejects_out_of_enum_side_value"
        status: pass
    human_judgment: false
  - id: D5
    description: "A resolved bench row with valid tenure renders a non-editable lock-icon box with the tenure-derived role; a missing-tenure bench row keeps the amber warning + Edit-person link with NO lock icon and NO bordered box — the two states share no markup"
    requirement: "RESOLVE-06"
    verification:
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_argument_role_cell_has_exactly_one_svg"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_missing_tenure_branch_shares_no_markup_with_locked_branch"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_missing_tenure_warning_and_lock_alternative_appear_exactly_once"
        status: pass
    human_judgment: true
    rationale: "Structurally the two branches are proven disjoint (no shared <svg>, no shared border-radius declaration), but whether the rendered result actually reads as visually distinct at a glance — the phase's own prohibition concern — is a visual judgment deferred to Plan 44-04's checkpoint against resolve-speakers-panel.png, per this plan's own <verification> item 6 and the prohibition's `flagged-unverified` status in the plan frontmatter."
  - id: D6
    description: "While a row's save is in flight, all three of that row's controls (toggle segments, Argument Role select, Descriptor input) are disabled, so a second submit for the same row cannot be issued before the first resolves; the existing per-row save-error message is unchanged"
    requirement: "RESOLVE-02"
    verification:
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_saving_flag_disables_all_three_row_controls"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-08-01
status: complete
---

# Phase 44 Plan 03: Segmented Bench/Advocate Toggle & Writable Argument Role Summary

**Replaces the overloaded `<select name="side">` with a two-segment Bench/Advocate toggle (which also absorbs the pre-resolution side gate) and a real four-option Argument Role dropdown for advocate rows, both writing through a single always-present hidden `side` input flushed synchronously before submit — closing a latent defect where the old gate path submitted with no side value at all.**

## Performance

- **Duration:** 25 min (approx., spanning file reads through the final Task 3 commit)
- **Started:** 2026-08-01T18:22:00Z (approx.)
- **Completed:** 2026-08-01T18:49:30Z
- **Tasks:** 3
- **Files modified:** 3 (1 new: DB round-trip test; 2 modified: `ResolveCard.svelte`, the shared pure-source contract test)

## Accomplishments

- **Segmented Bench/Advocate toggle, one submitting control (Task 1, RESOLVE-02):** Deleted the `<select name="side">` and the old two-plain-button gate entirely, replacing both with a single `sideToggle` snippet — a joined pill of two `<button type="button">` segments with `aria-pressed`, active fills `#4ade80` (Bench) / `#93c5fd` (Advocate), and neither active in the D-07 gate state. Added a single always-present `<input type="hidden" name="side" value={effectiveSide(row)} />` inside the per-row hidden form — the ONLY element in the file carrying that field name — fixing a latent defect where the pre-existing gate branch rendered no side-carrying control at all (a gate click previously submitted with no `side`, tripping the SvelteKit action's 400 guard). Added `toggleSide(row, choice)`: returns early (no state write, no submit) when the clicked segment is already active, otherwise delegates to the unchanged `confirmSide`/`onSideChange`. Imported `flushSync` from `svelte` and call it as the first statement of `submitRow`, before `requestSubmit()`, so a just-set `pendingSideOverrides` value reaches the DOM before the form serializes.
- **Writable Argument Role dropdown, lock affordance, preserved missing-tenure warning (Task 2, RESOLVE-03/RESOLVE-06):** Extracted the cell into `argumentRoleCell`, four branches checked in order — locked bench (valid tenure): a bordered box with an inline SVG padlock, `row.bench_role`, and a visually-hidden "Set from tenure, not editable" string; missing-tenure bench: unchanged amber warning + Edit-person link, now prefixed with the app-wide `⚠` glyph, sharing NO markup with the locked branch (no lock icon, no bordered box); editable non-bench (covers both advocate rows and gated rows, per delta #1): a real `<select>` with no `name`/`form` attribute and four options (`UNKNOWN`/"Select case role" placeholder, `PETITIONER`, `RESPONDENT`, `AMICUS`, labels sourced from the existing `SIDE_LABEL` map) — the placeholder's value is literally `UNKNOWN`, never an empty string or a disabled option; readonly non-bench: the pre-existing plain span. Added `chooseArgumentRole(row, value)`: satisfies the side gate the same way the toggle does when a role is picked before Bench/Advocate is explicitly chosen.
- **In-flight disabling and the RESOLVE-02/03/06 test lock (Task 3):** Added a `saving` parameter to `descriptorCell` (already present on `sideToggle`/`argumentRoleCell` from Tasks 1/2) and disabled its input while `saveState[participant_id].saving` is true — all three row controls now disable together, closing the concurrency gap. Extended `api/tests/test_phase44_resolve_table_contract.py` from 11 to 24 tests across three new banner-delimited sections (RESOLVE-02: singular hidden `side` input + form-region placement, `flushSync` import/call, toggle structure, no-op return, `confirmSide`/`onSideChange` preservation; RESOLVE-03: select singularity/no-name/no-form, option order, placeholder-value contract; RESOLVE-06: exactly-one-`<svg>`, missing-tenure/locked markup disjointness, saving-flag threading). Created `api/tests/test_phase44_argument_role_roundtrip.py` — Part 1 (no DB) parametrizes over all four dropdown values proving `ResolveRowUpdate` coerces each to its `SideEnum` member and that an out-of-enum value raises `pydantic.ValidationError` (T-44-03); Part 2 (DB-gated, `_db_configured()` skipif) seeds a job/argument/participant and round-trips `update_resolve_row_for_job` → `list_resolve_rows_for_job` for all three real advocate roles, re-asserting the BENCH-forces-descriptor-null rule (PJOB-15) at the round-trip level. **Verified against the live `scotus_test` database, not just schema-level** — all 3 parametrizations of the DB-gated round trip passed.

## Task Commits

Each task was committed atomically:

1. **Task 1: Segmented Bench/Advocate toggle, one submitted side value, and a flushed submit** - `c19ae2a2` (feat)
2. **Task 2: Argument Role — writable advocate dropdown, locked bench value, preserved missing-tenure warning** - `360c18b9` (feat)
3. **Task 3: In-flight disabling across all three row controls, plus the RESOLVE-02/03/06 test sections** - `bbaac48d` (test)

## Files Created/Modified

- `app/src/lib/components/ResolveCard.svelte` - `sideToggle`/`argumentRoleCell` snippets, `toggleSide`/`chooseArgumentRole` handlers, the hidden `side` input, `flushSync` in `submitRow`, `saving` threaded into all three row controls
- `api/tests/test_phase44_resolve_table_contract.py` - extended 11 → 24 tests (RESOLVE-02/03/06 sections)
- `api/tests/test_phase44_argument_role_roundtrip.py` - new: schema enum-boundary proof + DB-gated round trip

## Decisions Made

See `key-decisions` in frontmatter: `toggleSide`'s no-op-before-gate check ordering, `argumentRoleCell`'s branch conditions keyed purely on `side`/`missing_tenure`/`rowEditable` (not `gated`) per the plan's literal four-branch order, and reusing `SIDE_LABEL` for the dropdown's three real option labels rather than retyping them.

## Deviations from Plan

None beyond the design choices already called out above as `key-decisions` — those were resolved within the plan's own literal instructions, not treated as deviations requiring a rule citation.

## Issues Encountered

- **Literal-substring acceptance checks for `>Bench<`/`>Advocate<`/`>Edit person<`:** matching Plan 44-02's own documented fix for `>Change<`, my first draft of the toggle button labels and the "Edit person" link put the text content on its own line, inserting whitespace between the tag's `>` and the word and failing the literal `grep -c` acceptance checks. Fixed by collapsing each onto a single line (e.g. `>Bench</button>`), re-verified via `grep -c` returning 1 for each.
- **Duplicate `flushSync()` literal match from a doc comment:** my first draft of the explanatory comment above `flushSync()` in `submitRow` used the phrase "flushSync() forces the just-set..." — the literal substring `flushSync()` inside the comment made `awk '/function submitRow/,/^\t}/' | grep -c 'flushSync()'` return 2 instead of the plan's expected 1. Reworded the comment to "flushing here forces..." to avoid the duplicate literal match while keeping the explanation.
- **Full-suite pytest invocation quirk (pre-existing, documented in 44-01/44-02's own SUMMARYs):** running `./.venv/Scripts/python.exe -m pytest api/tests -q` directly (the plan's literal verification command) reproduces the same pre-existing failures 44-01 diagnosed and 44-02 re-confirmed — `tests/conftest.py`'s `TEST_DATABASE_URL` redirect isn't triggered when `tests/` isn't an ancestor of the invoked paths, so `test_admin_dev_routes.py` and `test_speakers_service.py` collide with the real dev DB, and `test_phase38_people_ui_contract.py`'s Node-subprocess fixture path bug still errors (4 errors, same file, same root cause). Re-ran with the corrected invocation `pytest tests/conftest.py api/tests -q`: **574 passed, 4 pre-existing errors (same file, same root cause), 0 failed** — exactly 44-02's baseline of 553 passed plus this plan's 21 new tests (13 added to the contract file, 8 in the new round-trip file), confirming zero regressions. Not re-documented as a new deferred item since it is identical to the one 44-01 already logged and 44-02 re-confirmed.

## Known Stubs

None. Every control in the reworked columns writes to and reads from real backend state — no hardcoded empty values, no placeholder-only components.

## Threat Flags

None. This plan's edits touch only the existing `?/saveResolveRow` per-row form-submit path (unchanged trust boundary) and add no new network endpoint, auth path, or schema change. The plan's own `T-44-03`/`T-44-11`/`T-44-12`/`T-44-13`/`T-44-14` threat register is the complete relevant set (all `mitigate`, each backed by a passing test in this plan's coverage above); `T-44-SC` (`accept`) correctly did not fire since no package-manager install occurred.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 44-04 can proceed: the segmented toggle, the Argument Role dropdown, the lock affordance, and the missing-tenure warning are all stable and backend-proven. Plan 44-04's own scope (the "Imported:" hint rework via `CopyableExtractedValue`'s new `prefixLabel` prop) touches only the hint `<div>`s below each cell, which this plan deliberately left untouched.
- Two coverage items in this plan (D2, D5) carry `human_judgment: true` — both are the same class of deferred visual/live-interaction check this phase has been carrying since Plan 44-02 (see that plan's D3 rationale), and both are explicitly deferred to Plan 44-04's checkpoint per this plan's own `<verification>` item 6 ("Full visual verification against the mockup is deferred to plan 44-04's checkpoint, once the hints land"). No new deferred item logged to `.planning/WINDOWS.md` — 44-02 already logged the shared deferred-visual-pass entry (id 2) that this plan's D2/D5 fold into.
- No blockers. The full-suite pytest invocation quirk is pre-existing (documented in 44-01, re-confirmed in 44-02 and again here) and confirmed unrelated to this plan's changes via the corrected invocation and the live DB-gated round-trip test passing cleanly.

---
*Phase: 44-resolve-table-rework*
*Completed: 2026-08-01*

## Self-Check: PASSED

- FOUND: `app/src/lib/components/ResolveCard.svelte`
- FOUND: `api/tests/test_phase44_resolve_table_contract.py`
- FOUND: `api/tests/test_phase44_argument_role_roundtrip.py`
- FOUND: `.planning/phases/44-resolve-table-rework/44-03-SUMMARY.md`
- FOUND: commit `c19ae2a2` (Task 1)
- FOUND: commit `360c18b9` (Task 2)
- FOUND: commit `bbaac48d` (Task 3)
- FOUND: commit `dc3429b3` (SUMMARY.md)
