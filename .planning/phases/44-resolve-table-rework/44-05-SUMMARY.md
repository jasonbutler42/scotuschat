---
phase: 44-resolve-table-rework
plan: 05
subsystem: ui
tags: [sveltekit, svelte5, resolve-table, dropdown-only, combobox, figma-reconciliation]

# Dependency graph
requires:
  - phase: 44-04
    provides: "Superseded checkpoint that surfaced the Figma canonical reconciliation doc (44-FIGMA-RECONCILE.md), locking the new four-column/dropdown-only design this plan implements"
provides:
  - "ResolveCard.svelte four-column table (Raw Label, Resolved As, Argument Role, Descriptor) — no Bench/Advocate column"
  - "personDropdown snippet — the single always-rendered searchable person control, stacked below sideToggle inside the merged Resolved As cell"
  - "personControlEditable(row, s) — the named review-set predicate gating which rows get the editable dropdown vs. the plain personDisplay"
  - "RowMatchState with disposition/correcting removed; allDispositioned keyed on personId alone; matchesJson left byte-identical"
  - "Seeding effect fallback to resolveRows' own committed person_id/full_name so an already-resolved row seeds as reviewed"
  - "api/tests/test_phase44_resolve_table_contract.py extended with a Plan 44-05 banner (9 new tests) plus 4 rewritten/inverted tests for the four-column dropdown-only contract"
affects: [44-06, 44-07, 44-08, 44-09]

# Actuals (#2632)
actuals:
  tokens: 27000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Single merged snippet (personDropdown) absorbing what used to be four mutually-exclusive Resolved-As render branches (gated-inert-button, correcting-combobox, resolved-plus-Change-link, unresolved-Select-person-link) into one always-rendered control, branching only on a named predicate (personControlEditable) rather than on a disposition/correcting state pair"
    - "Gate a data-carrying input via disabled/aria-disabled bound to a boolean, never via an {#if} wrapper around the input's own declaration (Phase 27 CR-01/CR-02, RESEARCH Pitfall 4) — applied here to the person combobox exactly as Plan 44-02 applied it to the Select-person button"

key-files:
  created: []
  modified:
    - api/tests/test_phase44_resolve_table_contract.py
    - app/src/lib/components/ResolveCard.svelte

key-decisions:
  - "Task 1's own aria-disabled contract check originally demanded a literal `aria-disabled=\"true\"` substring in the personDropdown snippet body. That is unworkable for a genuinely dynamic (gated vs. not) attribute bound to the same always-rendered input — the literal string can never appear in source next to a live boolean binding without either hardcoding bad accessibility (aria-disabled=\"true\" unconditionally) or duplicating the input into two conditional branches (which would break the exactly-one-role=\"combobox\" contract and reintroduce the {#if}-gated-input anti-pattern). Fixed the test in the same commit (Rule 1 — auto-fix a bug in a just-written test) to check the binding expression via regex (`aria-disabled=\\{[^}]*gated[^}]*\\}`) instead of a literal string."
  - "Reworded the file's own header comment (added in this same plan) after it tripped the identifier-absence assertions it was documenting — the prose describing what got deleted (mentioning `openPersonSearch` and the checkmark banner text by name) itself contained those retired literals, which `test_person_dropdown_is_always_rendered_not_click_revealed` and `test_dedicated_confirm_handler_and_retired_button_labels_are_gone` correctly flagged as still-present in source. Reworded to describe the deleted behavior without quoting the retired identifiers verbatim."
  - "Reworded two comments inside the `allDispositioned` derived body (the WR-04 early-true comment and the RESOLVE-08 comment above the return statement) to avoid the bare word 'disposition' — the plan's own acceptance criterion requires `grep -c 'disposition'` over that region to be exactly 0, and the original prose (accurately describing the old confirm/correct disposition machine) contained that word incidentally."

requirements-completed: []

coverage:
  - id: D1
    description: "The Resolve table renders exactly four <th scope=\"col\"> headers (Raw Label, Resolved As, Argument Role, Descriptor) in that order, with no Bench/Advocate header cell anywhere in the component"
    requirement: "RESOLVE-07"
    verification:
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_exactly_four_column_headers_declared"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_four_header_labels_appear_in_canonical_order"
        status: pass
    human_judgment: false
  - id: D2
    description: "Each row renders exactly four <td> cells; the Bench/Advocate toggle and the person control are stacked inside the single Resolved As cell, toggle above person control"
    requirement: "RESOLVE-07"
    verification:
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_row_renders_exactly_four_data_cells"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_side_toggle_and_person_control_share_the_resolved_as_cell"
        status: pass
    human_judgment: false
  - id: D3
    description: "The Resolved As person control is a single always-rendered searchable dropdown — never gated behind a Change/Select-person link — for every row in the review set; rows outside it (or the read-only card) keep the plain resolved-name display"
    requirement: "RESOLVE-08"
    verification:
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_person_dropdown_is_always_rendered_not_click_revealed"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_person_control_editable_predicate_exists"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_dedicated_confirm_handler_and_retired_button_labels_are_gone"
        status: pass
    human_judgment: false
  - id: D4
    description: "A row still behind the pre-resolution side gate renders the person input present-but-inert (disabled + aria-disabled bound to the gate + sr-only explanation), never removed from the DOM by an {#if} wrapper"
    requirement: "RESOLVE-08"
    verification:
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_gated_entry_point_is_genuinely_inert"
        status: pass
    human_judgment: false
  - id: D5
    description: "RowMatchState carries no disposition/correcting fields; allDispositioned keys on personId alone; matchesJson's ?/resolve wire payload shape ({raw_speaker_label, person_id}) is provably unchanged; the single name=\"side\" hidden input survives the column merge"
    requirement: "RESOLVE-08"
    verification:
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_row_match_state_has_no_confirm_correct_fields"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_all_dispositioned_gate_keys_on_person_id_only"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_matches_payload_shape_is_unchanged"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_single_side_input_survives_the_column_merge"
        status: pass
      - kind: integration
        ref: "api/tests/test_phase44_argument_role_roundtrip.py, api/tests/test_admin_jobs_phase25.py (DB-gated round trips, re-run after the merge)"
        status: pass
    human_judgment: false
  - id: D6
    description: "A row whose person is already committed seeds as reviewed (not un-reviewed) even if it still appears in the discrepancy list, so the review gate cannot disagree with what the table visibly shows"
    requirement: "RESOLVE-08"
    verification:
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_seeding_effect_falls_back_to_committed_person"
        status: pass
    human_judgment: false
  - id: D7
    description: "Operator visual acceptance of the merged four-column cell against Figma nodes 4205:81 (working card) and 4210:81 (all-resolved card) — hint stacking readability, gated/pre-filled/unresolved dropdown states, 860px responsive check, and read-only-card parity"
    verification: []
    human_judgment: true
    rationale: "Task 3 is a checkpoint:human-verify (gate=\"blocking\") by design — visual/interactive fidelity against a live Figma comparison cannot be established by a static source contract. Awaiting operator sign-off; see Awaiting Operator Verification section below."

duration: in progress (paused at Task 3 checkpoint)
completed: null
status: paused-checkpoint
---

# Phase 44 Plan 05: Four-Column Resolved-As Merge (RESOLVE-07/08) Summary — PAUSED AT CHECKPOINT

**Collapsed the Resolve table's standalone Bench/Advocate column into the Resolved As cell (toggle stacked above a new always-rendered `personDropdown` combobox) and deleted the confirm/correct disposition state machine entirely — Tasks 1 and 2 are committed and green; Task 3 (operator visual acceptance against Figma nodes 4205:81/4210:81) is an open `checkpoint:human-verify` awaiting the operator.**

## Performance

- **Duration so far:** ~50 min (Task 1 + Task 2)
- **Started:** 2026-08-04 (session start)
- **Tasks completed:** 2 of 3 (Task 3 is the open checkpoint)
- **Files modified:** 2 (`api/tests/test_phase44_resolve_table_contract.py`, `app/src/lib/components/ResolveCard.svelte`)

## Accomplishments

- **Task 1 — red-first contract rewrite:** Renamed/rewrote the five-column header-count and header-order tests to the four-column canonical order, with an explicit assertion that no `>Bench/Advocate<` header cell exists anywhere. Inverted the "single entry point" test (`test_open_person_search_is_the_one_entry_point` → `test_person_dropdown_is_always_rendered_not_click_revealed`) to assert `openPersonSearch` is deleted and exactly one always-rendered `role="combobox"` exists. Re-pointed the gated-entry-point test at the not-yet-written `personDropdown` snippet. Extended the retired-labels test with the Change link and the Corrected banner. Added a new "Plan 44-05" banner section with 8 new tests covering the four-data-cell row shape, the toggle+dropdown cell-sharing order, `RowMatchState`'s field removal, `allDispositioned`/`matchesJson`'s unchanged wire contract, the seeding effect's committed-person fallback, the surviving single `side` input, and the `personControlEditable` predicate. Verified the rewrite goes red against the pre-existing five-column component while the palette and no-`{@html}` guards stay green.
- **Task 2 — the tracer:** Deleted the standalone Bench/Advocate `<th>`/`<td>`; the merged Resolved As `<td>` now stacks `sideToggle`, its hint, the per-row save-error paragraph, the new `personDropdown` snippet, then the Resolved-As hint — in that literal order. `personDropdown` replaces the four-branch gated-button/correcting-combobox/resolved-plus-Change/unresolved-Select-person chain with one snippet: `personDisplay` for rows outside the review set (`!personControlEditable(row, s)`), otherwise the combobox unconditionally, gated via `disabled`/`aria-disabled` bound to the gate state (never an `{#if}` around the input itself) with a side-scoped placeholder ("Select bench…"/"Select advocate…"). Deleted `openPersonSearch`, the Change link, the Select-person link, and the Corrected banner; dropped `disposition`/`correcting` from `RowMatchState`; simplified `handleSelectPerson`/`handlePersonCreated` to write `personId` only. `allDispositioned` now keys on `personId` alone; `matchesJson` is byte-identical. The seeding `$effect` joins against the `resolveRows` prop (never `mergedRows`) so an already-committed row falls back to its own `person_id`/`full_name` instead of seeding as un-reviewed.
- **Verification:** `npm --prefix app run check` — 804 files, 0 errors, 36 warnings (identical count to the pre-existing baseline — no new warnings introduced). `pytest tests/conftest.py api/tests/test_phase44_resolve_table_contract.py api/tests/test_phase44_argument_role_roundtrip.py api/tests/test_admin_jobs_phase25.py` — 89 passed. Full suite `pytest tests/conftest.py api/tests` — 596 passed, 4 pre-existing collection errors (documented in every prior 44-0x SUMMARY as unrelated to this file), 0 failed.

## Task Commits

1. **Task 1: Rewrite the contract file's five-column and confirm/correct assertions to the four-column dropdown-only contract (red-first)** - `382f1cba` (test)
2. **Task 2: End-to-end four-column merged Resolved As cell with one always-rendered person dropdown** - `10baa898` (feat) — includes the aria-disabled test fix and the two comment rewordings described below (Rule 1, discovered mid-task)

## Files Created/Modified

- `api/tests/test_phase44_resolve_table_contract.py` - rewrote/inverted 4 existing tests, extended 1, added a 9-test "Plan 44-05" banner section (8 planned + 1 test fix), updated the module docstring
- `app/src/lib/components/ResolveCard.svelte` - deleted the Bench/Advocate `<th>`/`<td>`, added the `personDropdown` snippet and `personControlEditable` predicate, deleted `openPersonSearch`/the Change link/the Select-person link/the Corrected banner, simplified `RowMatchState`/`handleSelectPerson`/`handlePersonCreated`, updated `allDispositioned` and the seeding `$effect`

## Decisions Made

See `key-decisions` in frontmatter: the aria-disabled literal-string test fix (Rule 1), and the two comment rewordings needed because prose describing retired identifiers/words tripped the very identifier-absence and bare-word-count assertions it was near.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug in own Task 1 test] `aria-disabled="true"` literal-string check unworkable for a dynamic attribute**
- **Found during:** Task 2, running the contract suite against the new `personDropdown` implementation
- **Issue:** Task 1's `test_gated_entry_point_is_genuinely_inert` asserted the literal substring `'aria-disabled="true"'` in the snippet body. Because `personDropdown` renders exactly one combobox input for both gated and ungated states (per RESOLVE-08's "always-rendered, never duplicated" requirement, and the file's own `exactly-one-role="combobox"` contract), `aria-disabled` must be a live expression bound to `gated`, not a static literal — the two are mutually exclusive.
- **Fix:** Changed the assertion to a regex checking the binding expression (`aria-disabled=\{[^}]*gated[^}]*\}`) instead of the literal string.
- **Files modified:** `api/tests/test_phase44_resolve_table_contract.py`
- **Verification:** Full contract suite (46 tests) passes; the assertion still fails if `aria-disabled` is removed or unbound from `gated` (manually verified during authoring).
- **Committed in:** `10baa898` (Task 2 commit)

**2. [Rule 1 - Bug in own Task 2 prose] Retired identifiers/words quoted in new comments tripped identifier-absence assertions**
- **Found during:** Task 2, first pytest run after the rewrite
- **Issue:** Two new comments I wrote to document the deletion (the file's header comment, and the `allDispositioned` inline comments) accurately named the retired constructs (`openPersonSearch`, the checkmark banner text, the word "disposition") — which is exactly what `test_person_dropdown_is_always_rendered_not_click_revealed`'s blanket `"openPersonSearch" not in source` check and the plan's own `grep -c 'disposition'` acceptance criterion over the `allDispositioned` region correctly flagged as still-present.
- **Fix:** Reworded both comments to describe the deleted behavior without quoting the retired literals verbatim.
- **Files modified:** `app/src/lib/components/ResolveCard.svelte`
- **Verification:** Contract suite green; `awk '/let allDispositioned/,/^\t}\);/' | grep -c 'disposition'` returns 0.
- **Committed in:** `10baa898` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — bugs discovered in the plan's own just-authored test/prose, not in the plan's design)
**Impact on plan:** Both fixes are test/comment corrections with no effect on the shipped behavior's correctness or scope.

## Issues Encountered

None beyond the two auto-fixed items above.

## Known Stubs

None. Every control in the merged cell writes to and reads from real backend state — no hardcoded empty values, no placeholder-only components.

## Threat Flags

None beyond the plan's own threat register (T-44-15 through T-44-19, T-44-SC), all of which this plan's Task 2 satisfies per the plan's own coverage claims — no new network endpoint, auth path, or schema change was introduced.

## User Setup Required

None - no external service configuration required.

## Awaiting Operator Verification (Task 3 — checkpoint:human-verify, gate="blocking")

**Environment state at pause:**
- PostgreSQL (portable, `data/pgdata`) — already running (confirmed via `pg_ctl status`), Alembic at head (`0025`).
- SvelteKit dev server — started by this session, confirmed serving (`/admin/login` returns 200): **http://localhost:5173**
- FastAPI backend (port 8000) — **not reachable.** A pre-existing `python.exe` process (Windows PID 19032, path `C:\Users\jason\AppData\Local\Programs\Python\Python312\python.exe`, started 2026-08-03 15:56, i.e. from a prior day's session, not this project's `.venv`) is bound to port 8000 and is not serving working responses — the SvelteKit dev server's own `/cases` route returns 500 with it in place. I deliberately did **not** kill this process: it is unidentified from this session, killing an unrelated Windows process without confirmation is outside safe automation, and I have no way to confirm it isn't intentionally left running by the operator for an unrelated reason.
- **Action needed before verifying:** please confirm whether PID 19032 is stale (if so, end it and start the project's own FastAPI dev server — e.g. via your normal `scripts/dev-start.ps1` flow, or `./.venv/Scripts/python.exe -m uvicorn api.main:app --host 0.0.0.0 --port 8000`), then reload the pipeline job page. The SvelteKit dev server I started does not need to be restarted.

**Once the backend is reachable, verify per the plan's `<how-to-verify>`:**
1. Visit `http://localhost:5173/admin/pipeline/{job_id}` for a job at status `paused`, step `resolve` (use the Dev Tools reset-to-fixture control if no such job currently exists — fixture 15169).
2. Compare against Figma file `9PDECvbdHM2vYVxt3SCwru`, page "screen mockups for GSD", node `4205:81` (working card): four column headers in canonical order; toggle above the person control inside one cell; nothing overlapping.
3. Confirm the two stacked hint lines inside the merged cell read acceptably (one under the toggle, one under the dropdown) — say if one should go.
4. Confirm the dropdown is present+pre-filled on an auto-matched row, present+placeholder ("Select bench…"/"Select advocate…") on an unresolved row, and present-but-greyed on a row with no Bench/Advocate chosen yet.
5. Type into the dropdown on an unresolved row and pick a candidate — confirm the name lands in the input, no Corrected banner appears.
6. Click Bench then Advocate on a row's toggle — confirm it saves each time with no error.
7. Narrow the browser to ~860px — confirm the merged cell doesn't clip or overlap.
8. Open a completed/published argument's job page — confirm the read-only card still shows four headers and plain resolved names, not dropdowns.
9. Confirm rows already resolved and NOT in the review set show a plain name rather than a dropdown — say if you want that changed (it would mean widening a write path).

## Next Phase Readiness

- Plans 44-06 through 44-09 are blocked on this plan's Task 3 approval per the reconciliation doc's explicit sequencing ("Column merge is the largest single change; sequence it first, then layer copy/behaviour fixes on top").
- No code blockers — the four-column merge, the dropdown-only model, and both DB-gated save round trips (side save, `?/resolve` batch payload) are all proven green. The only open item is the operator's visual sign-off against the canonical Figma nodes.

---
*Phase: 44-resolve-table-rework*
*Paused: 2026-08-04, awaiting Task 3 checkpoint*
