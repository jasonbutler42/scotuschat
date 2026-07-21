---
phase: 37-tenure-seat-as-chief-associate-toggle
plan: "05"
subsystem: ui,api,database,testing
tags: [sveltekit, svelte5, fastapi, pydantic, alembic, aria, radiogroup]

requires:
  - phase: 37-03
    provides: CourtTenure.office ORM column, OFFICE_CHIEF/OFFICE_ASSOCIATE/VALID_OFFICES constants, office_title() formal-title helper, admin-people strict-write/tolerant-read schema split
  - phase: 37-04
    provides: office-based TenureEntry/speaker/admin-argument formal-title projections, tenure-public-title.browser.test.mjs
provides:
  - Office segmented native-radio editor in app/src/routes/admin/people/[id]/+page.svelte (fieldset/legend, role="radiogroup", 44px targets, #93c5fd selected/focus-visible state)
  - Validated, atomic office tenure form contract in app/src/routes/admin/people/[id]/+page.server.ts (allowlisted parsing, pre-PATCH validation, full-state fail() rehydration)
  - Completed app/tests/tenure-office.browser.test.mjs static regression contract (11/11 passing)
  - scripts/audit_tenure_seat_identifiers.py — assertion-capable, allowlist-based stale `seat` identifier gate over api/pipeline/app/tests
  - Disposable-database proof that the full 0019 -> 0020 -> audit -> execute -> 0021 migration sequence and downgrade/upgrade round trip work end to end against real application code
affects: []

tech-stack:
  added: []
  patterns:
    - "Native same-name radio pair (bind:group) inside a fieldset/legend for a two-value segmented control, with role=\"radiogroup\" carrying aria-invalid/aria-describedby (not the fieldset's implicit \"group\" role, and not the individual radios' \"radio\" role, per ARIA)"
    - "Submit-button onclick preventDefault() as a client preflight gate: calling event.preventDefault() in a <button type=\"submit\"> click handler cancels the browser's implicit form-submission activation behavior entirely, so use:enhance's own submit listener never fires — no separate cancel()/stopImmediatePropagation() plumbing needed"
    - "$state seeded from form ?? data with a companion $effect resync — the established pattern already used for isJustice/birthdate/tenureRows in this exact file, extended so a failed server action's returned state (including a still-unresolved Office selection) rehydrates without erasing other in-progress edits"
    - "Anchor static-regression-test markup extraction on a structural selector (<fieldset>/role=\"radiogroup\") instead of a bare keyword substring, so the extraction window can't be silently mis-scoped by an unrelated earlier identifier"

key-files:
  created:
    - scripts/audit_tenure_seat_identifiers.py
  modified:
    - app/src/routes/admin/people/[id]/+page.svelte
    - app/src/routes/admin/people/[id]/+page.server.ts
    - app/tests/tenure-office.browser.test.mjs
    - api/tests/test_admin_dashboard_stats.py
    - api/tests/test_admin_people_merge.py

key-decisions:
  - "office (and, when invalid, invalidOfficeOriginal) is stored per-row in TenureRow state exactly as D-11 requires: valid legacy/new rows hold 'chief'|'associate'; an invalid/blank legacy row holds office: null plus the verbatim original string, never a guessed default."
  - "aria-invalid and aria-describedby live on a role=\"radiogroup\" div nested inside the fieldset, not on the fieldset itself (whose implicit role is \"group\", which ARIA does not permit aria-invalid on) and not on the individual radio inputs (role \"radio\" also does not permit it) — resolved via svelte-check's a11y_role_supports_aria_props_implicit warning, not guessed."
  - "tenure-office.browser.test.mjs's officeMarkup() helper was fixed (not the assertions) to anchor on the actual <fieldset>/role=\"radiogroup\" element instead of the bare substring \"Office\" — a naive substring search matches whichever TypeScript identifier (e.g. invalidOfficeOriginal, necessarily declared in <script> before the markup) contains \"Office\" first, mis-scoping the 8000-char extraction window away from the real UI entirely. This is a bug-fix to the test's own anchor logic (Rule 1), not a weakening of any assertion — every original assertion is unchanged and all 11 still pass."
  - "scripts/audit_tenure_seat_identifiers.py uses an exact (path, line-number, line-text) allowlist rather than a fuzzy pattern-based exception matcher, so a genuinely new stale seat reference cannot slip in as an accidental near-match of an existing exception, and a documented exception whose line has since moved or changed also fails loudly (stale-allowlist detection) instead of silently over-permitting."

requirements-completed: [PEOPLE-08]

coverage:
  - id: D1
    description: "Operators edit tenure Office through an accessible native-radio Chief/Associate control (44px targets, locked color/focus states, role=\"radiogroup\"); a new row defaults to Associate; an invalid/blank legacy value is never coerced, stays visible with an associated role=\"alert\" message, and blocks the whole profile save until explicitly corrected; the shared Save Person action persists Office atomically with dates and other tenure fields."
    requirement: PEOPLE-08
    verification:
      - kind: automated_ui
        ref: "app/tests/tenure-office.browser.test.mjs (11 static-regression assertions covering markup/ARIA/keyboard-semantics/default/invalid-state/focus/serialization/server-validation/rehydration contracts)"
        status: pass
      - kind: other
        ref: "npm run check --prefix app (svelte-check): 0 errors"
        status: pass
    human_judgment: false
  - id: D2
    description: "The full staged migration sequence (pre-37 schema -> 0020 rename -> non-writing default audit -> reviewed-report execute with explicit resolutions -> 0021 CHECK+NOT NULL -> downgrade/upgrade round trip) and the application's model/schema/service/import/projection/editor contract work together against the fully-constrained schema, proven on a disposable database that is never the shared scotus/scotus_test DB."
    requirement: PEOPLE-08
    verification:
      - kind: integration
        ref: "One-shot disposable-database harness (deleted after use): seeded formal/numbered/unresolved legacy office values at revision 0019, applied 0020/audit/execute/0021/downgrade+re-upgrade, then ran api/tests/test_admin_people_schemas_service.py, pipeline/tests/test_import_justices_csv.py, api/tests/test_speakers_service.py, api/tests/test_admin_arguments_service.py, api/tests/test_admin_dashboard_stats.py against it — 149 passed"
        status: pass
      - kind: integration
        ref: "tests/test_migrate_tenure_offices.py + the same five application modules run against the normal configured TEST_DATABASE_URL — 177 passed"
        status: pass
    human_judgment: false
  - id: D3
    description: "No unclassified active `seat` identifier remains anywhere in api/, pipeline/, app/, or tests/ — every remaining whole-word hit is an exact, explicitly documented migration-history or legacy-fixture exception; the audit script exits nonzero on any unclassified hit, missing root, unreadable file, or stale (no-longer-matching) documented exception."
    requirement: PEOPLE-08
    verification:
      - kind: other
        ref: "python scripts/audit_tenure_seat_identifiers.py — PASS (21 documented exceptions, all matched, zero unclassified hits); manually verified fail-closed behavior with an injected unclassified hit (exit 1) and a corrupted allowlist entry (exit 1)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The full repository test suite, frontend static check, and both Phase 37 browser regressions (Office editor, public formal-title display) pass together as the final phase-closing gate."
    requirement: PEOPLE-08
    verification:
      - kind: unit
        ref: ".\\.venv\\Scripts\\python.exe -m pytest (full suite) — 527 passed, 5 xfailed (pre-existing, unrelated to this phase)"
        status: pass
      - kind: automated_ui
        ref: "node app/tests/tenure-office.browser.test.mjs (11 passed) and node app/tests/tenure-public-title.browser.test.mjs (1 passed, real headless-Edge CDP run)"
        status: pass
    human_judgment: false

duration: 90min
completed: 2026-07-21
status: complete
---

# Phase 37 Plan 05: Office Editor, Migration Proof, and Final Stale-Identifier Gate Summary

**Free-text tenure Seat replaced end-to-end by an accessible native-radio Chief/Associate control, with a disposable-database proof that the staged migration and application layers agree, and a fail-closed repository audit confirming zero stray `seat` identifiers remain**

## Performance

- **Duration:** ~90 min
- **Completed:** 2026-07-21
- **Tasks:** 3
- **Files modified:** 6 (1 created)

## Accomplishments

- **Office editor (Task 1).** `app/src/routes/admin/people/[id]/+page.svelte`'s free-text Seat input is gone. Each tenure row now has an `Office` `<fieldset>`/`<legend>` containing two native same-name radios (`bind:group={row.office}`, values `"chief"`/`"associate"`) styled as the established segmented-toggle idiom (44px targets, `#93c5fd` selected/border/focus, `:focus-visible` outline via a `:has()` CSS rule on the visually-hidden-but-focusable radio input). A new row defaults to `associate` (D-10); an invalid or blank legacy value is stored as `office: null` plus the verbatim `invalidOfficeOriginal`, is never coerced, and renders a persistent `role="alert"` message (`Unrecognized office: "…". Select Chief or Associate before saving.` / `No office was recorded. …`) associated via `aria-describedby`/`aria-invalid` on a `role="radiogroup"` div (not the fieldset's implicit `group` role, and not the radios' own `radio` role — ARIA does not permit `aria-invalid` on either).
- **Atomic, validated save (Task 1).** The shared `Save Person` submit button's `onclick` preflights every tenure row; if any is unresolved, it calls `event.preventDefault()` (cancelling the browser's implicit form-submission activation entirely — no fetch, no partial PATCH), shows `Select Chief or Associate for every tenure period before saving.`, and focuses the first unresolved group. `+page.server.ts`'s `save` action validates every row's `office` against the `chief`/`associate` allowlist before issuing any PATCH, and every `fail()` path now returns the complete submitted profile/tenure state (`full_name`/`first_name`/…/`birthdate`/`is_justice`/`tenures`) so a failed save rehydrates everything — including a still-invalid Office selection — via a `$effect` keyed on `form?.tenures`, without erasing unrelated in-progress edits.
- **Blocking migration proof (Task 2).** `api/tests/test_admin_dashboard_stats.py`'s two remaining `CourtTenure(seat="Associate Justice", ...)` fixtures became `office="associate"`. On a fully disposable, throwaway Postgres database (created and dropped by a one-shot harness script, never touching the shared `scotus`/`scotus_test` databases), the complete coordinated sequence was exercised and proven: pre-37 (0019) schema seeded with formal (`Chief Justice`/`Associate Justice`), numbered (`Associate Justice Seat 3`), and one deliberately unresolved legacy value → 0020 rename → default (dry-run) audit confirmed **zero writes** → executed with the reviewed report and an explicit resolution for the unresolved row → 0021 (CHECK + NOT NULL) succeeded only once every row was canonical → downgrade 0021→0020 and re-upgrade proved safe constraint-drop-before-nullable-relax ordering → the five application-level pytest modules (admin-people schemas/service, justices CSV import, speakers/admin-arguments projections, dashboard stats) all passed against the fully-constrained schema (149 passed). The plan's own scoped verify command also passes end to end (177 passed).
- **Final stale-identifier gate (Task 3).** New `scripts/audit_tenure_seat_identifiers.py` walks `api/`, `pipeline/`, `app/`, and `tests/` for whole-word `seat`/`Seat` and fails closed on anything not an exact `(file, line, text)` match against a documented allowlist of 21 entries in two categories — `migration-history` (prose documenting the D-17 rename) and `legacy-fixture` (test code intentionally constructing/asserting a legacy value, or asserting one is absent). It also fails if a scan root is missing, a file can't be read, or a documented exception's line no longer matches the repository (stale-allowlist detection). Verified fail-closed manually with an injected unclassified hit and a corrupted allowlist entry (both exit 1). Final gate: full pytest suite 527 passed / 5 xfailed (pre-existing); `npm run check` 0 errors; both Phase 37 browser regressions pass in full (11 + 1); audit script exits 0.

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement accessible Office state, serialization, and recovery** - `4611f5a2` (feat)
2. **Task 2: Run blocking migration-to-application verification** - `fbe4a49a` (test)
3. **Task 2/3 deviation: fix merge-test raw tenure inserts missing required office** - `1a9acdef` (fix)
4. **Task 3: Run final Nyquist and stale-identifier gates** - `20020945` (test)

## Files Created/Modified

- `app/src/routes/admin/people/[id]/+page.svelte` - Office segmented native-radio editor replacing the free-text Seat input; client-side preflight/focus/rehydration logic.
- `app/src/routes/admin/people/[id]/+page.server.ts` - `office`-allowlisted, validated, atomic tenure save action with full-state `fail()` rehydration.
- `app/tests/tenure-office.browser.test.mjs` - `officeMarkup()` anchor fixed to target the actual `<fieldset>`/`role="radiogroup"` element instead of a bare keyword substring (all 11 original assertions unchanged and now passing).
- `api/tests/test_admin_dashboard_stats.py` - Two remaining `CourtTenure(seat=...)` fixtures converted to canonical `office=`.
- `api/tests/test_admin_people_merge.py` - Three raw-SQL `INSERT INTO court_tenures (person_id) VALUES (:pid)` statements now also supply the now-required `office` value.
- `scripts/audit_tenure_seat_identifiers.py` - New assertion-capable, allowlist-based stale `seat` identifier repository audit.

## Decisions Made

- Kept `office`/`invalidOfficeOriginal` as two distinct fields on `TenureRow` (rather than overloading `office` to carry an arbitrary raw string when invalid) exactly matching the plan's own action text and D-11 — a valid row's `office` is always `'chief'`/`'associate'`, an invalid row's is always `null`, with the original text preserved separately for the error message.
- Moved `aria-invalid`/`aria-describedby` onto a nested `role="radiogroup"` div rather than the outer `<fieldset>` or the individual radios, after `svelte-check`'s `a11y_role_supports_aria_props_implicit` warning surfaced that ARIA does not permit `aria-invalid` on the fieldset's implicit `"group"` role or on the radios' own `"radio"` role — `"radiogroup"` is the one role in this markup ARIA does permit it on.
- Used a submit-button `onclick` preflight (calling `event.preventDefault()` to cancel the button's implicit form-submission activation) rather than threading validation through `use:enhance`'s `cancel()` callback — this keeps the existing `use:enhance` block completely untouched and gives a single, simple gate that works regardless of internal `use:enhance`/`onclick` listener ordering, since a prevented click never even reaches the `submit` event.
- Fixed `tenure-office.browser.test.mjs`'s `officeMarkup()` anchor logic (not its assertions) after discovering that TypeScript identifiers required by other assertions in the same file (`invalidOfficeOriginal`, necessarily declared in `<script>` before the markup) contain the substring "Office" and would otherwise become the *first* match, moving the 8000-character extraction window entirely away from the real fieldset. Anchoring on `<fieldset`/`role="radiogroup"` instead is a more correct, structural anchor for what the helper is actually trying to find — a Rule 1 bug fix to test infrastructure, not a weakened assertion.
- Fixed `api/tests/test_admin_people_merge.py`'s three raw-SQL tenure-row inserts (Rule 1) even though this file was not in the plan's declared `files_modified` — Task 3's `<verify>` runs the full, unscoped pytest suite, and these inserts would otherwise violate the 0021 migration's `NOT NULL`/`CHECK` constraint whenever `DATABASE_URL` is configured, which is exactly the kind of full-suite-blocking regression Task 3's gate exists to catch.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test infrastructure bug] `officeMarkup()`'s keyword-substring anchor mis-scoped the extraction window**
- **Found during:** Task 1, first run of `app/tests/tenure-office.browser.test.mjs` against the new implementation.
- **Issue:** `officeMarkup()` located the extraction window via `source.indexOf('Office')` — but the same file's `TenureRow` interface necessarily declares `invalidOfficeOriginal` (required by other assertions in the very same test file) in `<script>`, before the markup. Since `"Office"` (capital O) is a substring of `"invalidOfficeOriginal"`, that identifier became the *first* match, moving the ±(1000/7000)-character window entirely away from the real `<fieldset>`/radio markup — 3 of 11 assertions failed even though the implementation was correct.
- **Fix:** Anchored the helper on `<fieldset|role="radiogroup"` (the actual structural element being tested) instead of the bare word.
- **Files modified:** `app/tests/tenure-office.browser.test.mjs`
- **Verification:** All 11 original assertions (unchanged) now pass; the fix was tested by confirming the anchor still finds the correct element regardless of earlier `Office`-containing identifiers.
- **Committed in:** `4611f5a2` (part of Task 1's commit)

**2. [Rule 1 - Bug] Merge-test raw tenure inserts violated the new NOT NULL/CHECK office constraint**
- **Found during:** Task 3's full, unscoped pytest-suite run (flagged proactively before running, per dispatch guidance, and confirmed present).
- **Issue:** `api/tests/test_admin_people_merge.py` seeded `court_tenures` rows via `INSERT INTO court_tenures (person_id) VALUES (:pid)` with no `office` value, in three tests. This was silently fine while `office`/`seat` was nullable but now violates the 0021 migration's `NOT NULL` + `CHECK (office IN ('chief','associate'))` constraint whenever `DATABASE_URL` is configured, blocking `test_get_merge_preview_counts_tenures`, `test_delete_person_if_orphan_blocked_by_tenure`, and `test_merge_people_transfers_tenures`.
- **Fix:** Each insert now also supplies `office = 'associate'`.
- **Files modified:** `api/tests/test_admin_people_merge.py`
- **Verification:** Full pytest suite passes (527 passed, 5 xfailed) with `DATABASE_URL` configured.
- **Committed in:** `1a9acdef`

---

**Total deviations:** 2 auto-fixed (both Rule 1 — bug fixes, no scope creep).
**Impact on plan:** Both fixes were strictly necessary for the plan's own stated gates (Task 1's browser-test acceptance criteria; Task 3's full-suite gate) to pass honestly. No architectural changes, no scope beyond what each task's own verify step required.

## Issues Encountered

- `npx svelte-check` via WSL-native `node` failed with an unrelated environment error (`Cannot find module @rollup/rollup-linux-x64-gnu`) — this WSL-side `node_modules` is evidently mismatched for this session (opposite of the environment state noted in 37-04, where the Windows side was broken and WSL worked). Resolved by running `npm run check` via `powershell.exe` against the Windows-native install (per this session's environment notes, `app/node_modules` is now a real Windows-native install), which succeeded cleanly (0 errors).
- `npm run check` reports 3 net-new `state_referenced_locally` informational warnings on the `isJustice`/`birthdate`/`tenureRows` `$state(form?.X ?? data.person.X)` initializers (form-rehydration support added in Task 1). This is the same established pattern already used in this exact file (and elsewhere in the codebase, e.g. `admin/pipeline/[job_id]/+page.svelte`'s `liveJob`) for "seed local mutable state from a prop, resync via `$effect`" — Svelte's linter cannot statically see the paired `$effect`. Not treated as a defect; documented here per the plan's own Nyquist gate rather than silently absorbed. Warning count: 16 (pre-Phase-37, per 37-04's self-check) → 19 (this plan), all of this same class plus 0 new a11y/type errors.

## Known Stubs

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 37 (tenure-seat-as-chief-associate-toggle) is fully implemented across database, API, import, editor, and read-only display, with PEOPLE-08 satisfied end to end and a repository-wide audit proving no stale `seat` identifier remains outside 21 documented, exact exceptions.
- The disposable-database migration harness used for Task 2's proof was a one-shot script, deleted after use — it created and dropped its own throwaway database and never touched the shared `scotus`/`scotus_test` databases; no residual artifacts remain in the repository or in Postgres.
- Orchestrator note: this is the last plan in Phase 37 — phase-level verification and ROADMAP phase-completion status are handled separately after this plan's completion is reported back.

## Self-Check: PASSED

- `app/src/routes/admin/people/[id]/+page.svelte`, `app/src/routes/admin/people/[id]/+page.server.ts`, `app/tests/tenure-office.browser.test.mjs`, `api/tests/test_admin_dashboard_stats.py`, `api/tests/test_admin_people_merge.py`, `scripts/audit_tenure_seat_identifiers.py` — all exist and contain the expected changes.
- Commits `4611f5a2`, `fbe4a49a`, `1a9acdef`, `20020945` all exist in `git log --oneline`.
- `node app/tests/tenure-office.browser.test.mjs` (Windows-native): 11 passed, 0 failed.
- `node app/tests/tenure-public-title.browser.test.mjs` (Windows-native, real headless-Edge CDP): 1 passed, 0 failed.
- `npm run check --prefix app` (Windows-native): 0 errors, 19 warnings (all pre-existing-pattern `state_referenced_locally`, none new a11y/type).
- `.\.venv\Scripts\python.exe -m pytest -q` (full suite): 527 passed, 5 xfailed.
- `.\.venv\Scripts\python.exe -m pytest tests/test_migrate_tenure_offices.py api/tests/test_admin_people_schemas_service.py pipeline/tests/test_import_justices_csv.py api/tests/test_speakers_service.py api/tests/test_admin_arguments_service.py api/tests/test_admin_dashboard_stats.py -x` (plan's own Task 2 verify command): 177 passed.
- `.\.venv\Scripts\python.exe scripts/audit_tenure_seat_identifiers.py`: PASS, 21 documented exceptions, all matched, zero unclassified hits.

---
*Phase: 37-tenure-seat-as-chief-associate-toggle*
*Completed: 2026-07-21*
