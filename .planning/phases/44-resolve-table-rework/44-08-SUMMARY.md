---
phase: 44-resolve-table-rework
plan: 08
subsystem: ui
tags: [svelte, sveltekit, resolve-card, figma-reconciliation, bench-role, accessibility]

# Dependency graph
requires:
  - phase: 44-resolve-table-rework
    provides: "44-06's descriptor-preservation write-path fix and live tenure-recompute regression lock; 44-07's sourcePrefix derived value and side-scoped candidates that this plan's edits sit alongside untouched"
provides:
  - "benchRoleState(row, side) — the single named predicate driving all three mutually-exclusive bench Argument Role states, checked before rowEditable so the read-only card renders them identically (RESOLVE-11)"
  - "Canonical bench copy: 'Calculated from tenure', 'Tenure not found', '(resolve person first)' replacing the retired ingestion-prefixed 'N/A - ...' hints (RESOLVE-12, RESOLVE-14)"
  - "Edit person link opens in a new tab (target=\"_blank\" rel=\"noopener\") with the arrow glyph isolated in an aria-hidden span (RESOLVE-11)"
  - "Bench-conditional Descriptor hint — the hint call site wrapped in {#if side !== 'BENCH'}, preserving the stored value and the advocate-row hint unchanged (RESOLVE-13)"
affects: [44-09]

actuals:
  tokens: 9800
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Named state predicate (benchRoleState) returning a closed union, driving markup branches from its result rather than repeating the same three conditions inline — keeps an ordering-sensitive rule (unresolved must be checked before calculated) in exactly one place"
    - "Wrap-not-delete for suppressed hints: both the Argument Role and Descriptor hint call sites stayed byte-identical for advocate rows; the bench suppression is a call-site {#if} condition around the existing call, never a change to the shared CopyableExtractedValue component"

key-files:
  created: []
  modified:
    - app/src/lib/components/ResolveCard.svelte
    - api/tests/test_phase44_resolve_table_contract.py

key-decisions:
  - "benchRoleState checks person_id == null (unresolved) before !missing_tenure (calculated) — verified against api/services/admin_people.py that an unresolved bench participant reports missing_tenure=false, so the reverse order would render an empty locked box for an unresolved row."
  - "The retired 44-04 test asserting the two ingestion-prefixed bench hint strings live inside argumentRoleHintValue was renamed (not just edited) to test_hint_value_helpers_exist_and_bench_fork_left_the_hint_layer and inverted to assert those strings are gone and the helper no longer forks on missing_tenure — matching the plan's literal instruction."
  - "A second, plan-unlisted 44-02 assertion (test_descriptor_cell_snippet_always_renders_bench_dash_and_editable_input) broke because it banned the literal string \"side !== 'BENCH'\" anywhere in descriptorCell's body — a check written before RESOLVE-13 required a legitimate wrap around the hint. Widened (not weakened): it now asserts the data-carrying <input> renders before and outside that wrapper, preserving the original Phase 27 CR-01/CR-02 intent (the input itself must never be conditionally rendered) while accommodating the new hint suppression."

requirements-completed: [RESOLVE-11, RESOLVE-12, RESOLVE-13, RESOLVE-14]

coverage:
  - id: T1
    description: "Three mutually-exclusive bench Argument Role states (unresolved/calculated/missing-tenure) with canonical copy, checked in the order the service's null-person_id/missing_tenure=false quirk requires; Edit person link opens in a new tab with rel=\"noopener\" and an aria-hidden arrow glyph"
    requirement: "RESOLVE-11, RESOLVE-12, RESOLVE-14"
    verification:
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_bench_role_state_predicate_exists_and_orders_unresolved_first"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_bench_role_state_ignores_editability"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_edit_person_link_opens_in_a_new_tab_with_noopener"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_edit_person_accessible_name_excludes_the_glyph"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_unresolved_bench_copy_present_once_and_carries_no_dash"
        status: pass
    human_judgment: true
    rationale: "Static source contracts prove the three-way fork exists, is ordered correctly, and doesn't key on editability, but the operator-visible states in a live browser session were not exercised end-to-end (no frontend test runner exists in this repo, per 39-RESEARCH.md). Visual confirmation against Figma nodes 4205:81/4206:111 is deferred to 44-09's acceptance checkpoint, per this plan's own verification section."
  - id: T2
    description: "Bench Descriptor cell renders a single muted dash with no hint line; the CopyableExtractedValue call and its wrapper div are conditionally rendered on non-bench side, unchanged in props; no change to the shared component or api/services/"
    requirement: "RESOLVE-13"
    verification:
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_descriptor_hint_is_bench_conditional"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_bench_descriptor_branch_renders_only_a_dash"
        status: pass
      - kind: command
        ref: "git diff --stat api/services/ app/src/lib/components/CopyableExtractedValue.svelte app/src/lib/components/CreatePersonPopover.svelte across this plan's commit range — empty"
        status: pass
    human_judgment: false
  - id: T3
    description: "13 new Plan 44-08 tests plus two re-pointed stale assertions; full api/tests suite and npm run check green"
    requirement: "RESOLVE-11, RESOLVE-12, RESOLVE-13, RESOLVE-14"
    verification:
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py (77 passed)"
        status: pass
      - kind: unit
        ref: "api/tests (632 passed, 4 pre-existing collection errors, 0 failures)"
        status: pass
      - kind: command
        ref: "npm --prefix app run check (804 files, 0 errors, 36 pre-existing warnings)"
        status: pass
    human_judgment: false
---

# Phase 44 Plan 08: Bench copy, new-tab Edit person link, read-only parity Summary

**Bench Argument Role now renders one of three states in the operator's own words — `Calculated from tenure`, `Tenure not found`, or `(resolve person first)` — instead of the interim `Imported: N/A - ...` hint wording, and the tenure-fix path opens in a second tab so the live recompute 44-06 locked is actually usable.**

## What Was Built

**Task 1.** Restructured `argumentRoleCell` around a new named predicate, `benchRoleState(row, side)`, returning `'unresolved' | 'calculated' | 'missing-tenure' | null`. The three bench branches now key only on `side`, `row.person_id`, and `row.missing_tenure` — never on `rowEditable` — which is what makes the read-only card render them identically to the editable card. The unresolved check runs first (`(resolve person first)`, no box, no lock, no dash, no hint) because the service reports `missing_tenure: false` for an unresolved bench row; checking the calculated branch first would otherwise render an empty locked box. The calculated branch keeps the locked box verbatim and adds `Calculated from tenure` beneath it. The missing-tenure branch keeps the amber `⚠ Missing tenure` warning verbatim, adds `Tenure not found` beneath it, and the `Edit person` link now carries `target="_blank"` and `rel="noopener"`, with the `↗` glyph isolated in its own `aria-hidden="true"` span so the accessible name stays exactly "Edit person". `argumentRoleHintValue`'s bench branch was deleted (it now only answers for the three advocate sides), and the Argument Role `<td>`'s `CopyableExtractedValue` call was wrapped in `{#if side !== 'BENCH'}` rather than deleted, keeping advocate rows and 44-07's four-derived-prefix contract unaffected.

**Task 2.** `descriptorCell`'s hint block (the `CopyableExtractedValue` call and its `margin-top` wrapper) was wrapped in the same `{#if side !== 'BENCH'}` condition. A bench row now renders exactly one thing: the muted en-dash span. The call's props are byte-identical to what 44-07 left them; suppression is a render condition only, and the stored `ArgumentParticipant.descriptor` stays intact per 44-06's write-path fix (confirmed by an empty diffstat on `api/services/` and `CopyableExtractedValue.svelte`).

**Task 3.** Added a `Plan 44-08` banner (13 new tests) to `api/tests/test_phase44_resolve_table_contract.py` covering: the three canonical copy strings each appearing exactly once, the retired ingestion-prefixed strings being gone, the Argument Role hint's bench-conditional wrap, the unresolved branch carrying no dash and no hint call, `benchRoleState`'s existence/ordering/editability-independence, the Edit-person link's new-tab attributes and accessible name, the Descriptor hint's bench-conditional wrap, the bench Descriptor branch rendering only a dash, all three bench branches (via both `argumentRoleCell` and `benchRoleState`) being independent of the editability flag, and the `<thead>` region carrying no editability reference. Re-pointed the stale 44-04 assertion (renamed to `test_hint_value_helpers_exist_and_bench_fork_left_the_hint_layer`) to assert the inverse of what it checked before. The two 44-03 structural guards (`test_argument_role_cell_has_exactly_one_svg`, `test_missing_tenure_branch_shares_no_markup_with_locked_branch`) needed no changes and pass unmodified.

## Task Commits

1. **Task 1: Three bench Argument Role states with canonical copy, and a new-tab Edit person link** — `c9066822` (feat)
2. **Task 2: Bench Descriptor cell renders a bare dash with no hint line** — `27de119c` (feat)
3. **Task 3: Contract tests for the bench copy, the new-tab link, and read-only parity** — `4e1012fe` (test)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] A second, plan-unlisted 44-02 assertion broke and required re-pointing**

- **Found during:** Task 3, running the full contract file per its own verify command.
- **Issue:** `test_descriptor_cell_snippet_always_renders_bench_dash_and_editable_input` (44-02's original section, not named in this plan's Task 3 action list — only the 44-04 helper assertion and the 44-03 structural guards were called out) asserted `"side !== 'BENCH'" not in body` for `descriptorCell`. That check predates RESOLVE-13's requirement to wrap the hint in exactly that condition, so Task 2's mandated change tripped it.
- **Fix:** Widened rather than weakened: the test now asserts the data-carrying `<input>` renders before and outside the `{#if side !== 'BENCH'}` wrapper (`input_idx < hint_condition_idx`), preserving the original Phase 27 CR-01/CR-02 guarantee (the input itself must never be conditionally rendered) while allowing the hint below it to be bench-gated.
- **Files modified:** `api/tests/test_phase44_resolve_table_contract.py` (already this plan's declared Task 3 file).
- **Commit:** `4e1012fe` (part of Task 3's commit).

**2. [Rule 1 - Bug] Two comments accidentally duplicated the exact literal strings the acceptance criteria count**

- **Found during:** Task 1, running the acceptance-criteria grep checks after the initial edit.
- **Issue:** A code comment explaining the missing-tenure branch's markup distinctness quoted the exact string `"Calculated from tenure"`, and another comment explaining the new-tab link quoted the exact string `rel="noopener"` — both inflating `grep -c` counts the plan's acceptance criteria require to be exactly 1.
- **Fix:** Reworded both comments to describe the same intent without repeating the literal strings verbatim.
- **Files modified:** `app/src/lib/components/ResolveCard.svelte`.
- **Commit:** `c9066822` (Task 1, pre-commit — caught during the same task's own verification pass, not a separate commit).

**3. [Rule 1 - Bug] A third comment self-matched its own snippet-scoped grep count**

- **Found during:** Task 2, running the acceptance-criteria grep checks.
- **Issue:** A comment inside `descriptorCell` explaining why suppression must be a call-site condition named the shared component (`CopyableExtractedValue.svelte's ...`), which the acceptance criteria's `awk`-scoped grep counted as a second `CopyableExtractedValue` reference inside the snippet (expected exactly 1: the real call site).
- **Fix:** Reworded the comment to say "the shared hint component" instead of naming the component literally.
- **Files modified:** `app/src/lib/components/ResolveCard.svelte`.
- **Commit:** `27de119c` (Task 2).

### Auth Gates

None encountered.

### Prohibited Actions Avoided

- No change to `api/services/admin_people.py`, `api/services/admin_jobs.py`, or any other file under `api/services/` — confirmed empty diffstat across this plan's commit range.
- No change to `CopyableExtractedValue.svelte` or `CreatePersonPopover.svelte` — confirmed empty diffstat.
- No new hex color introduced — the palette guard test (`test_no_unapproved_hex_colors_introduced`, `test_palette_guard_still_passes_with_hint_additions`) still passes; the new copy strings use only `#94a3b8` and `#fbbf24`, both already approved.
- No stored value cleared, blanked, or reassigned to represent a missing tenure window as a derived value — the calculated and missing-tenure branches keep sharing no markup and no wording (locked box + `Calculated from tenure` vs. amber warning + `Tenure not found` + edit link).

## Verification

- `npm --prefix app run check` — 804 files, **0 errors**, 36 pre-existing warnings (unrelated to this plan's file — none in `ResolveCard.svelte` beyond the one pre-existing a11y warning on the listbox `<li>`, unchanged by this plan).
- `./.venv/Scripts/python.exe -m pytest tests/conftest.py api/tests/test_phase44_resolve_table_contract.py -q` — **77 passed**, 0 failures.
- `./.venv/Scripts/python.exe -m pytest tests/conftest.py api/tests -q` — **632 passed**, 0 failures, the same 4 pre-existing collection errors documented in every prior 44-0x SUMMARY (Node.js path issue in `test_phase38_people_ui_contract.py`, unrelated to this plan).
- `grep -c 'Calculated from tenure' app/src/lib/components/ResolveCard.svelte` — 1.
- `grep -c 'Tenure not found' app/src/lib/components/ResolveCard.svelte` — 1.
- `grep -c '(resolve person first)' app/src/lib/components/ResolveCard.svelte` — 1.
- `grep -c 'N/A - from tenure' app/src/lib/components/ResolveCard.svelte` — 0; same for `N/A - tenure not found` — 0.
- `grep -c 'rel="noopener"' app/src/lib/components/ResolveCard.svelte` — 1, on the same anchor as `target="_blank"`.
- `grep -c 'prefixLabel={sourcePrefix}' app/src/lib/components/ResolveCard.svelte` — 4 (unchanged from 44-07 — both suppressed hints were wrapped, not deleted).
- `git diff --stat api/services/ app/src/lib/components/CopyableExtractedValue.svelte app/src/lib/components/CreatePersonPopover.svelte` across this plan's commit range — empty.
- `git diff --name-only` (uncommitted working tree at plan end) shows only pre-existing, not-mine changes (`.env.example`, `app/.env.example`, `app/vite.config.ts`, `scripts/dev-start.ps1`, a todos-directory move) plus this plan's own already-committed files — no unexpected file was touched.

Item 8 of the plan's own `<verification>` section (visual confirmation of the three bench states against Figma nodes 4205:81 and 4206:111) is explicitly deferred to 44-09's operator acceptance checkpoint, per the plan's own text.

## Self-Check: PASSED

- FOUND: `app/src/lib/components/ResolveCard.svelte`
- FOUND: `api/tests/test_phase44_resolve_table_contract.py`
- FOUND: commit `c9066822` (Task 1)
- FOUND: commit `27de119c` (Task 2)
- FOUND: commit `4e1012fe` (Task 3)
