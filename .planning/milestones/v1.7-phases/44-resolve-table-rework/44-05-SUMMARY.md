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
  - "Task 3 checkpoint remediation: create-person moved inside the open combobox popup, a decorative chevron affordance, a neutral gated placeholder, and lastAdvocateRole preserving a chosen advocate role across a Bench/Advocate toggle round trip"
affects: [44-06, 44-07, 44-08, 44-09]

# Actuals (#2632)
actuals:
  tokens: 31000
  tasks: 2
  commits: 3

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
  - "Task 3 checkpoint remediation (continuation): the operator rejected the first Task 3 checkpoint with 9 checklist items plus additional feedback. Triaged each against the actual 44-06..44-09 PLAN.md files (not assumed) before fixing anything — see 'Task 3 Checkpoint Remediation' section below for the full breakdown of what was fixed now vs. confirmed already scheduled."
  - "Fixed a real data-loss bug found during re-verification, not by the operator's original 9-step list but surfaced by their own free-form testing: `side` is the single stored column for both the Bench/Advocate toggle and the specific advocate role (PETITIONER/RESPONDENT/AMICUS); `toggleSide`'s Advocate branch unconditionally wrote 'UNKNOWN', discarding a previously-chosen specific role on every Bench→Advocate round trip. Fixed client-side with a `lastAdvocateRole` memory map — this bug pre-dates this plan (present since 44-03) but was fixed now per explicit instruction that data loss is never acceptable regardless of scope boundaries."
  - "Did NOT preemptively fix the bench-descriptor server-side null-forcing bug (`api/services/admin_jobs.py`'s `update_resolve_row_for_job`) even though it is also a data-loss mechanism the operator's toggle testing would hit. That fix is 44-06 Task 2's exact, already-fully-specified target, with its own required red-first test inversion in `test_admin_jobs_phase25.py` (44-06 Task 1's acceptance criteria explicitly require the suite to fail against 'today's' service before the fix lands). Patching `admin_jobs.py` now would either break 44-06's own red-first precondition or require duplicating its test-inversion work outside this plan's declared `files_modified`. Documented prominently below instead so the operator knows this exact defect is one plan away, not silently dropped."

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
    rationale: "Task 3 is a checkpoint:human-verify (gate=\"blocking\") by design — visual/interactive fidelity against a live Figma comparison cannot be established by a static source contract. First checkpoint attempt was rejected with specific defects (see 'Task 3 Checkpoint Remediation' below); confirmed-in-scope defects are fixed and re-verified via the automated suite, and a fresh checkpoint is awaiting operator sign-off."
  - id: D8
    description: "Task 3 checkpoint remediation: create-person renders inside the open combobox popup, the combobox carries a visual affordance icon, the gated placeholder is side-neutral, and toggling Bench/Advocate preserves a previously-chosen specific advocate role"
    requirement: "RESOLVE-07/RESOLVE-08 (checkpoint defect fixes, not new requirements)"
    verification:
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_create_person_trigger_lives_inside_the_open_listbox_popup"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_person_combobox_has_a_dropdown_affordance_icon"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_person_dropdown_placeholder_is_neutral_while_gated"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_toggle_side_preserves_a_previously_chosen_advocate_role"
        status: pass
    human_judgment: false

duration: ~70min (Tasks 1-2 + Task 3 remediation cycle)
completed: 2026-08-07
status: complete
---

# Phase 44 Plan 05: Four-Column Resolved-As Merge (RESOLVE-07/08) Summary

**Collapsed the Resolve table's standalone Bench/Advocate column into the Resolved As cell (toggle stacked above a new always-rendered `personDropdown` combobox) and deleted the confirm/correct disposition state machine entirely. The first Task 3 checkpoint was rejected with specific defects; confirmed-in-scope defects (create-person placement, combobox affordance, neutral gated placeholder, and a toggle data-loss bug) were fixed and covered by new regression tests. The operator approved the second Task 3 checkpoint on 2026-08-07 — plan complete.**

## Performance

- **Duration so far:** ~50 min (Task 1 + Task 2) + ~40 min (Task 3 checkpoint remediation)
- **Started:** 2026-08-04 (session start)
- **Tasks completed:** 2 of 3 (Task 3 is the open checkpoint, now on its second iteration)
- **Files modified:** 2 (`api/tests/test_phase44_resolve_table_contract.py`, `app/src/lib/components/ResolveCard.svelte`)

## Accomplishments

- **Task 1 — red-first contract rewrite:** Renamed/rewrote the five-column header-count and header-order tests to the four-column canonical order, with an explicit assertion that no `>Bench/Advocate<` header cell exists anywhere. Inverted the "single entry point" test (`test_open_person_search_is_the_one_entry_point` → `test_person_dropdown_is_always_rendered_not_click_revealed`) to assert `openPersonSearch` is deleted and exactly one always-rendered `role="combobox"` exists. Re-pointed the gated-entry-point test at the not-yet-written `personDropdown` snippet. Extended the retired-labels test with the Change link and the Corrected banner. Added a new "Plan 44-05" banner section with 8 new tests covering the four-data-cell row shape, the toggle+dropdown cell-sharing order, `RowMatchState`'s field removal, `allDispositioned`/`matchesJson`'s unchanged wire contract, the seeding effect's committed-person fallback, the surviving single `side` input, and the `personControlEditable` predicate. Verified the rewrite goes red against the pre-existing five-column component while the palette and no-`{@html}` guards stay green.
- **Task 2 — the tracer:** Deleted the standalone Bench/Advocate `<th>`/`<td>`; the merged Resolved As `<td>` now stacks `sideToggle`, its hint, the per-row save-error paragraph, the new `personDropdown` snippet, then the Resolved-As hint — in that literal order. `personDropdown` replaces the four-branch gated-button/correcting-combobox/resolved-plus-Change/unresolved-Select-person chain with one snippet: `personDisplay` for rows outside the review set (`!personControlEditable(row, s)`), otherwise the combobox unconditionally, gated via `disabled`/`aria-disabled` bound to the gate state (never an `{#if}` around the input itself) with a side-scoped placeholder ("Select bench…"/"Select advocate…"). Deleted `openPersonSearch`, the Change link, the Select-person link, and the Corrected banner; dropped `disposition`/`correcting` from `RowMatchState`; simplified `handleSelectPerson`/`handlePersonCreated` to write `personId` only. `allDispositioned` now keys on `personId` alone; `matchesJson` is byte-identical. The seeding `$effect` joins against the `resolveRows` prop (never `mergedRows`) so an already-committed row falls back to its own `person_id`/`full_name` instead of seeding as un-reviewed.
- **Verification:** `npm --prefix app run check` — 804 files, 0 errors, 36 warnings (identical count to the pre-existing baseline — no new warnings introduced). `pytest tests/conftest.py api/tests/test_phase44_resolve_table_contract.py api/tests/test_phase44_argument_role_roundtrip.py api/tests/test_admin_jobs_phase25.py` — 89 passed. Full suite `pytest tests/conftest.py api/tests` — 596 passed, 4 pre-existing collection errors (documented in every prior 44-0x SUMMARY as unrelated to this file), 0 failed.
- **Task 3 checkpoint remediation (continuation):** the operator ran the first Task 3 checkpoint against the live app and rejected it with specific defects. Fixed the items confirmed in this plan's own scope: (1) restructured `personDropdown` so `CreatePersonPopover` renders inside the open listbox popup (a bordered footer row beneath the candidate `<ul>`, inside the same floating panel) instead of as a standalone element always visible beneath the input; (2) added a decorative, `aria-hidden` chevron `<svg>` to the always-rendered person input so it visually reads as a combobox; (3) made the gated placeholder read `Select person…` (side-neutral) instead of guessing `Select bench…`/`Select advocate…` from an unconfirmed, possibly ingestion-guessed side; (4) fixed a real client-side data-loss bug in `toggleSide` — the Advocate segment unconditionally wrote `'UNKNOWN'`, discarding a previously-chosen specific advocate role (`PETITIONER`/`RESPONDENT`/`AMICUS`) on every Bench→Advocate round trip, since `side` is the single stored column for both the toggle and the specific role. Added a `lastAdvocateRole` per-row memory map, consulted by `toggleSide` and populated by `chooseArgumentRole`, so the round trip now restores the operator's choice. Four new regression tests lock all four fixes in the static source contract. Full verification re-run: `npm --prefix app run check` — 0 errors, 36 warnings (unchanged baseline); `pytest tests/conftest.py api/tests/test_phase44_resolve_table_contract.py api/tests/test_phase44_argument_role_roundtrip.py api/tests/test_admin_jobs_phase25.py` — 93 passed; full suite `pytest tests/conftest.py api/tests` — 600 passed, the same 4 pre-existing unrelated collection errors, 0 failed.

## Task Commits

1. **Task 1: Rewrite the contract file's five-column and confirm/correct assertions to the four-column dropdown-only contract (red-first)** - `382f1cba` (test)
2. **Task 2: End-to-end four-column merged Resolved As cell with one always-rendered person dropdown** - `10baa898` (feat) — includes the aria-disabled test fix and the two comment rewordings described below (Rule 1, discovered mid-task)
3. **Task 3 checkpoint remediation: fix create-person placement, combobox affordance, neutral gated placeholder, and toggle data-loss bug** - `9a94edfd` (fix)

## Files Created/Modified

- `api/tests/test_phase44_resolve_table_contract.py` - rewrote/inverted 4 existing tests, extended 1, added a 9-test "Plan 44-05" banner section (8 planned + 1 test fix), updated the module docstring; continuation adds a "Task 3 checkpoint remediation" section with 4 new regression tests and a `_if_block` brace-balanced helper
- `app/src/lib/components/ResolveCard.svelte` - deleted the Bench/Advocate `<th>`/`<td>`, added the `personDropdown` snippet and `personControlEditable` predicate, deleted `openPersonSearch`/the Change link/the Select-person link/the Corrected banner, simplified `RowMatchState`/`handleSelectPerson`/`handlePersonCreated`, updated `allDispositioned` and the seeding `$effect`; continuation restructures the combobox popup, adds the chevron icon, the neutral gated placeholder, and the `lastAdvocateRole` toggle fix

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

## Task 3 Checkpoint Remediation (continuation after first checkpoint rejection)

The operator tested the running app against the plan's original 9-step checklist plus free-form
observations and reported specific defects instead of approving. Per the resume instructions, each
reported item was triaged against the **actual** 44-06/44-07/44-08/44-09 PLAN.md files (read in full,
not assumed) before anything was fixed.

### Confirmed already owned by an upcoming plan (not fixed here — would duplicate or destabilize that plan's own red-first tracer choreography)

| Operator-reported item | Confirmed owner | Why not fixed now |
|---|---|---|
| "Create new person" is a standalone button, not part of the dropdown | **Fixed in this continuation** (see below) — this one was genuinely 44-05's own scope | — |
| Dropdown "just looks like a regular text box" | **Fixed in this continuation** (see below) | — |
| All people shown regardless of Bench/Advocate — dropdown "not filtered by bench/advocate" | `44-07-PLAN.md` Task 1, `sideScopedCandidates(discrepancy, label, side, gated)`, RESOLVE-09 | 44-07 threads `is_justice` through two currently-too-narrow TypeScript annotations and adds the filter function with an explicit fail-open rule; implementing a partial version now would conflict with 44-07's own named-function/fail-open contract tests |
| No "auto-matched"/"needs you" tag on rows | `44-09-PLAN.md` Task 2, `rowCueTag(row, s)`, RESOLVE-16 | 44-09 requires the tag comparison to key off `auto_match_id` vs. the *current* `personId` (so an operator-changed row loses the tag) — this is 44-09's own disclosure-gap closure (T-44-19), with its own ordering and contract-test requirements |
| No "N of M speakers…" progress pill / "Continue Resolve" only appears once complete | `44-09-PLAN.md` Task 1, `reviewProgress`, RESOLVE-15 | 44-09 requires the progress count and the Continue gate to read one shared predicate so they can never disagree — a partial implementation now risks exactly the disagreement its own first prohibition forbids |
| "Edit person" link not opening in a new tab | `44-08-PLAN.md` Task 1, RESOLVE-11 (`target="_blank" rel="noopener"`) | Bundled with 44-08's larger three-way bench Argument Role rework (`benchRoleState`); the link change alone is small but its contract test lives inside that same task's banner |
| Bench descriptor data loss (server-side null-forcing on a BENCH write) | `44-06-PLAN.md` Task 2, `update_resolve_row_for_job`, RESOLVE-13 | This is exactly 44-06's stated target, down to the exact source line. 44-06 Task 1's own acceptance criteria require the test suite to go **red** against today's still-buggy service before Task 2's fix lands. Patching `api/services/admin_jobs.py` now (outside this plan's declared `files_modified`) would make 44-06 Task 1's red-first precondition impossible to satisfy without a second, duplicate inversion of `test_admin_jobs_phase25.py`. See the dedicated write-up below — this is a real, live bug the operator will hit again before 44-06 runs, and it is not being silently dropped. |
| Ingestion correctly identifies bench side but doesn't fill out resolve properly | **Not owned by any plan in 44-05..44-09** | Confirmed via full read of all four plan files — this is a pipeline/ingestion-layer concern (how `pipeline/commands/resolve.py` populates `ArgumentParticipant.side`/`person_id` at ingest time), not a `ResolveCard.svelte` rendering concern. Recommend filing as a new backlog item for a future phase; the operator self-flagged this as likely out of scope, which this triage confirms. |

### Fixed now (confirmed in 44-05's own scope, or genuine data loss)

1. **Create-person moved inside the open combobox popup.** `CreatePersonPopover` now renders as a
   bordered footer row inside the same floating panel as the candidate `<ul>`, only while
   `s.comboOpen` is true — not as an always-visible standalone element beneath the input. Matches
   Figma node 4205:81's popup affordance. Locked by
   `test_create_person_trigger_lives_inside_the_open_listbox_popup`.
2. **Combobox visual affordance added.** A decorative, `aria-hidden` chevron `<svg>` (muted
   `#94a3b8`, already-approved palette) now sits inside the input so the always-rendered control
   reads as a dropdown rather than a plain text box. Locked by
   `test_person_combobox_has_a_dropdown_affordance_icon`.
3. **Gated placeholder made neutral.** While a row's side has not yet been chosen (`gated` true),
   the placeholder now reads `Select person…` instead of guessing `Select bench…`/`Select advocate…`
   from `effectiveSide(row)` — which could reflect an ingestion-guessed, unconfirmed side (this is
   exactly what the operator's screenshot showed: an unresolved bench-guessed row rendering
   `Select bench…` before the operator had confirmed anything). Locked by
   `test_person_dropdown_placeholder_is_neutral_while_gated`. The side-specific placeholders still
   render once the gate is actually resolved.
4. **Toggle data-loss bug fixed.** `toggleSide`'s Advocate branch previously wrote the literal
   `'UNKNOWN'` unconditionally on every click. Because `side` is the single stored column for both
   the Bench/Advocate toggle and the specific advocate role (`PETITIONER`/`RESPONDENT`/`AMICUS` are
   `side` values, not a separate field), this discarded a previously-chosen specific role on every
   Bench→Advocate round trip — exactly the operator's item 6. Added `lastAdvocateRole`, a per-row
   memory populated by `chooseArgumentRole` and consulted by `toggleSide`, with a fallback to the
   row's own already-committed `side` when the operator hasn't touched the select this session. This
   bug pre-dates this plan (present since 44-03's `toggleSide`) but is fixed now per explicit
   instruction that data loss is never acceptable regardless of which plan "owns" the file. Locked by
   `test_toggle_side_preserves_a_previously_chosen_advocate_role`.

**On the descriptor half of item 6 specifically:** toggling to Bench and back does *not* fully
recover a previously-typed descriptor today, because the root cause is server-side
(`update_resolve_row_for_job` unconditionally nulls `ArgumentParticipant.descriptor` on any BENCH
write, regardless of what the client sends) — no client-side fix can prevent data already nulled in
the database from coming back. This is precisely 44-06 Task 2's target, with its own red-first test
inversion already fully specified in `44-06-PLAN.md`. **This is a known, live, one-plan-away
regression** — please treat it as expected until 44-06 lands, not a re-report.

### Investigated, not fixed (Step 3 — hint independence, item 3)

Checked via `git log -p` blame on `resolvedAsHintValue`/`sideHintValue`/`argumentRoleHintValue`: all
three were introduced in commit `cdcf6a89` (**plan 44-04**, not 44-05), and 44-05's Task 2 diff
(`10baa898`) only relocated the `resolvedAsHintValue` call site into the merged cell — it did not
touch any hint-value helper body or add/remove a call site. **Factual finding: the "hints mirror the
current field value instead of a frozen import-time snapshot" behavior is 100% pre-existing from
44-04, not introduced or altered by this plan.**

It is also not an oversight — `44-CONTEXT.md` D-08 explicitly documents why: *"there is no separate
stored 'originally extracted' value... `ArgumentParticipant.side` has no shadow/history column...
Any hint on Bench/Advocate or Argument Role would necessarily just redisplay the row's own current
value."* Building real per-row provenance so a hint could differ from the live field is already
recorded under `44-CONTEXT.md`'s own "Deferred Ideas" section ("Capturing genuinely distinct
raw/extracted values for `side` and argument role at parse time... a future phase could add this").
The click-to-copy affordance on non-editable/imported hints (also flagged by the operator) is a
`CopyableExtractedValue`-level design question that none of 44-06..44-09 touch either. **Recommend
filing both as a new backlog item** rather than reopening this plan's scope — no plan in the current
44-05..44-09 set claims either.

### Item 9 reworded (operator was unsure what it meant)

The original wording ("rows that are already resolved and NOT in the review set show a plain name
rather than a dropdown") describes a specific row state — a committed `person_id` on a row that is
**not** in the current `discrepancies` list — that the operator's test fixture likely doesn't
contain. Reworded below to be self-contained and to note the fixture requirement explicitly.

## Task 3 Checkpoint — Approved 2026-08-07 (second attempt)

The operator verified the checklist below against the running app and Figma nodes 4205:81/4210:81 and replied "approved". No further defects reported.

**Environment:** both dev servers are already running natively on Windows and reachable from each
other (FastAPI at `http://localhost:8000`, SvelteKit at `http://localhost:5173`) — no restart should
be needed for this re-verification pass.

**Verify per the corrected/reworded checklist below (Figma nodes 4205:81 working card / 4210:81
all-resolved card, file `9PDECvbdHM2vYVxt3SCwru`, page "screen mockups for GSD"):**

1. Visit `http://localhost:5173/admin/pipeline/{job_id}` for a job at status `paused`, step `resolve`
   (use the Dev Tools reset-to-fixture control if no such job currently exists — fixture 15169).
2. Compare against node `4205:81`: four column headers in canonical order; toggle above the person
   control inside one cell; nothing overlapping.
3. Confirm the create-person option now appears **inside** the open dropdown's popup (click into an
   editable person field to open it) rather than as a separate button below the input.
4. Confirm the person input now visually reads as a dropdown (a chevron icon) rather than a plain
   text box.
5. Confirm the two stacked hint lines inside the merged cell read acceptably (one under the toggle,
   one under the dropdown) — say if one should go. **Known, not re-fixable here:** the hint text
   mirrors the field's current value rather than a frozen import-time snapshot; this is pre-existing
   from 44-04 and tracked as a backlog item, not a defect of this plan.
6. Confirm the dropdown is present+pre-filled on an auto-matched row, present+side-specific
   placeholder (`Select bench…`/`Select advocate…`) on an unresolved-but-side-chosen row, and now
   shows a **neutral** `Select person…` placeholder (present-but-greyed) on a row where Bench/Advocate
   has genuinely not been chosen yet.
7. Type into the dropdown on an unresolved row and pick a candidate — confirm the name lands in the
   input, no Corrected banner appears.
8. Click Bench then Advocate on a row's toggle where you had already chosen a specific Argument Role
   (e.g. Respondent's Counsel) — confirm the specific role is now preserved across the round trip
   instead of resetting to the placeholder. **Known, not fixed here (next plan, 44-06):** the
   Descriptor value on that same row will still not survive a Bench round trip today, because the
   server currently nulls it in the database on any BENCH write regardless of the client — this is
   44-06 Task 2's exact, already-specified target.
9. Narrow the browser to ~860px — confirm the merged cell doesn't clip or overlap.
10. Open a completed/published argument's job page — confirm the read-only card still shows four
    headers and plain resolved names, not dropdowns.
11. Find or create a row whose `person_id` is already committed but which does **not** appear in the
    current pipeline job's discrepancy list (i.e. an already-resolved speaker outside the active
    review set — this may require a fixture with more speakers than currently have open discrepancies)
    and confirm it shows a plain name rather than a dropdown — say if you want that changed (it would
    mean widening a write path). If no such row exists in your current fixture, this step can be
    skipped and re-tried once one does.

**Not re-tested here because they are confirmed owned by upcoming plans** (see triage table above —
please do not re-report these at this checkpoint): unfiltered candidate dropdown (44-07), missing
auto-matched/needs-you tags (44-09), missing progress pill / Continue-always-visible (44-09),
same-tab Edit-person link (44-08), and the descriptor round-trip data loss (44-06, noted in step 8
above).

## Next Phase Readiness

- Plans 44-06 through 44-09 are blocked on this plan's Task 3 approval per the reconciliation doc's explicit sequencing ("Column merge is the largest single change; sequence it first, then layer copy/behaviour fixes on top").
- No code blockers — the four-column merge, the dropdown-only model, and both DB-gated save round trips (side save, `?/resolve` batch payload) are all proven green, and the checkpoint-remediation fixes are proven by 4 new regression tests plus a full green suite (600 passed, same 4 pre-existing unrelated collection errors, `npm run check` 0 errors). The only open item is the operator's visual sign-off against the canonical Figma nodes.
- 44-06 should be aware, when it runs, that its Task 2 fix (`api/services/admin_jobs.py`) is still fully unimplemented — this continuation deliberately did not touch it, so 44-06 Task 1's red-first precondition is intact.

---
*Phase: 44-resolve-table-rework*
*Paused: 2026-08-05, awaiting Task 3 checkpoint (second attempt, post-remediation)*
