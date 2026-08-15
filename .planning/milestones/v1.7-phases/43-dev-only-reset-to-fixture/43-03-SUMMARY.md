---
phase: 43-dev-only-reset-to-fixture
plan: 03
subsystem: app
tags: [sveltekit, svelte5-runes, admin, dev-tooling, form-actions, env-gating]

# Dependency graph
requires:
  - phase: 43-dev-only-reset-to-fixture (Plan 43-01)
    provides: POST /api/admin/dev/reset-to-fixture, ResetToFixtureResponse contract (fixtures[].conversation_id/case_name/role/argument_id/argument_status/admin_job_status), the conditionally-mounted admin_dev router
  - phase: 43-dev-only-reset-to-fixture (Plan 43-02)
    provides: full four-fixture reseed + state realization behind that same endpoint, so this plan's Success list always shows all four fixtures
provides:
  - app/src/routes/admin/+page.server.ts::isDevelopment — server-only $env/dynamic/private-derived boolean threaded into /admin's load return
  - app/src/routes/admin/+page.server.ts::actions.resetToFixture — zero-input SvelteKit form action proxying to the backend endpoint, mapping every failure to exactly one of two locked UI-SPEC error copies
  - app/src/routes/admin/+page.svelte — Dev Tools section (DEV ONLY badge, Idle/Confirming/Running/Success/Error states) as the last section on /admin, entirely inside {#if data.isDevelopment}
  - tests/test_admin_dev_frontend_gate.py — DB-free source-invariant guard (4 tests) proving the gate, the env-boundary, the zero-input-surface, and the two-error-copy set
affects: [43-04-live-uat]

# Actuals (#2632)
actuals:
  tokens: 6000
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "$env/dynamic/private (not $env/static/private) for any SvelteKit server-only value that must be a request-time, not build-time, decision — the same codebase must serve both dev and prod without a separate build artifact (D-07)"
    - "Source-invariant pytest guard (read the .svelte/.ts files as plain text, no DB/server) for proving a server-side conditional gate and an env-boundary, when a full browser-driven test would require standing up a second server process just to flip one per-deployment constant"

key-files:
  created:
    - tests/test_admin_dev_frontend_gate.py
  modified:
    - app/src/routes/admin/+page.server.ts
    - app/src/routes/admin/+page.svelte

key-decisions:
  - "ENVIRONMENT is read via $env/dynamic/private, not $env/static/private like ADMIN_TOKEN/FASTAPI_BASE_URL in the same file — static-private values are inlined by Vite at build time, which would make the Dev Tools gate a build-time decision and require a separate build artifact for prod vs dev (D-07 explicitly forbids this)."
  - "resetToFixture does not redirect on success — it returns the parsed fixtures array under a stable resetFixtures key so the Success state can render inline on the same page, matching the UI-SPEC's Success state (not the redirect-after-mutate pattern the other /admin actions use)."
  - "A parsed fixtures array with anything other than exactly 4 entries is treated as the mid-reset error, never a shorter success list — the UI-SPEC's 'partial' row explicitly forbids a '2 of 4 reseeded' rendering."
  - "Did NOT mark DEVTOOL-01/DEVTOOL-02 complete in REQUIREMENTS.md, despite this plan's frontmatter listing both. Plan 43-04 (this phase's final plan) closes both requirements by actually attempting the production-refusal case end-to-end (view-source + a direct 404 against the reset endpoint) — marking them complete here, before that live demonstration runs, would misstate phase status. Mirrors 43-01-SUMMARY's and 43-02-SUMMARY's identical decision and rationale."

patterns-established:
  - "Source-invariant guard pattern for a server-decided frontend gate: read the two frontend files as text, assert (a) the gated heading is unique, (b) it sits between the gate's opening index and its file-final matching close (index comparison, not a Svelte parse), (c) no CSS-hiding mechanism or dialog/modal import exists, and (d) the gated value never crosses into a client-visible env prefix or a .svelte file."

requirements-completed: []  # DEVTOOL-01/02 intentionally NOT marked — see key-decisions; Plan 43-04 closes both

coverage:
  - id: D1
    description: "isDevelopment is computed server-side at request time from a server-only dynamic env var; the raw ENVIRONMENT string never appears in +page.svelte or as a PUBLIC_-prefixed variable in +page.server.ts"
    requirement: "DEVTOOL-02"
    verification:
      - kind: unit
        ref: "tests/test_admin_dev_frontend_gate.py#test_environment_not_client_exposed"
        status: pass
      - kind: unit
        ref: "tests/test_admin_dev_frontend_gate.py#test_dev_tools_section_is_server_gated"
        status: pass
    human_judgment: false
  - id: D2
    description: "The Dev Tools heading sits inside {#if data.isDevelopment} (index-order proven), with no CSS display:none/visibility:hidden rule and no dialog/popover import anywhere in the file — the section's absence outside development is a server omission, never a client-side hide"
    requirement: "DEVTOOL-02"
    verification:
      - kind: unit
        ref: "tests/test_admin_dev_frontend_gate.py#test_dev_tools_section_is_server_gated"
        status: pass
    human_judgment: false
  - id: D3
    description: "resetToFixture reads no form data and references no corpus path — the destructive action's only input is the operator's Confirm reset click"
    requirement: "DEVTOOL-01"
    verification:
      - kind: unit
        ref: "tests/test_admin_dev_frontend_gate.py#test_reset_action_posts_no_operator_input"
        status: pass
    human_judgment: false
  - id: D4
    description: "Exactly the two UI-SPEC-locked error copies exist verbatim in +page.server.ts, with no third 'Reset failed' variant"
    requirement: "DEVTOOL-02"
    verification:
      - kind: unit
        ref: "tests/test_admin_dev_frontend_gate.py#test_error_copies_match_ui_spec"
        status: pass
    human_judgment: false
  - id: D5
    description: "Both modified frontend files are svelte-check clean, and the Dev Tools section's Svelte/TS surface introduces zero new type errors"
    requirement: "DEVTOOL-01"
    verification:
      - kind: unit
        ref: "cd app && npm run check -- 804 files, 0 errors, 36 pre-existing warnings (unchanged from baseline)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Full pytest suite is green with no regressions from adding the 4 new frontend-gate tests"
    requirement: "DEVTOOL-01, DEVTOOL-02"
    verification:
      - kind: integration
        ref: "./.venv/Scripts/python.exe -m pytest -q -- 841 passed, 5 xfailed, 4 pre-existing errors (backlog 999.10, unrelated)"
        status: pass
    human_judgment: false

duration: ~40min
completed: 2026-07-31
status: complete
---

# Phase 43 Plan 3: Dev-Only Reset to Fixture — Frontend Confirm UI Summary

**`/admin` now renders a server-gated "Dev Tools" section (DEV ONLY badge, two-step Confirm/Cancel, Running spinner, four-fixture Success list, `role="alert"` Error state) wired to Plan 43-01/43-02's backend endpoint through a zero-input SvelteKit form action, with the environment value read server-side only and never exposed to the browser.**

## Performance

- **Duration:** ~40 min
- **Tasks:** 3 completed
- **Files modified:** 3 (2 modified, 1 created)

## Accomplishments
- `app/src/routes/admin/+page.server.ts` — `isDevelopment` added to the load return, derived from `$env/dynamic/private`'s `ENVIRONMENT` (deliberately not the static-private import the file's other three vars use, per D-07's request-time-not-build-time requirement); `actions.resetToFixture` proxies to `POST /api/admin/dev/reset-to-fixture` with the `X-Admin-Token` header, reads no form data, and maps every failure path (404, other non-ok, thrown fetch, unparseable JSON, or a fixtures array that isn't exactly 4 entries) to exactly one of the UI-SPEC's two locked error copies
- `app/src/routes/admin/+page.svelte` — new Dev Tools section as the last section on the page, entirely inside `{#if data.isDevelopment}`: Idle (button-only, no submit) → Confirming (full wipe-scope statement + Confirm reset/Cancel row) → Running (in-place spinner, all controls non-interactive) → Success (badge + one line per reseeded fixture, `invalidateAll()` refreshing the rest of the page) → Error (`role="alert"`, control returns to Idle not Confirming)
- `tests/test_admin_dev_frontend_gate.py` — 4 new DB-free, server-free tests proving the gate's structural correctness, the environment-value boundary, the reset action's zero-input surface, and the exact two-error-copy set; closes 43-VALIDATION.md's third Wave 0 item with the reasoning recorded in the module docstring
- `cd app && npm run check`: 804 files, 0 errors, 36 pre-existing warnings (identical baseline before and after all three tasks — no new warnings introduced)
- Full suite: 841 passed, 5 xfailed, 4 pre-existing errors (backlog 999.10, confirmed out of scope per this plan's own known-preexisting-failure note)

## Task Commits

Each task was committed atomically:

1. **Task 1: Server-side environment gate and the resetToFixture action (D-07)** - `6c533cc3` (feat)
2. **Task 2: The Dev Tools section — five states, two-step confirm (D-05, D-06)** - `6465b893` (feat)
3. **Task 3: Source-invariant guard for the server-side gate (DEVTOOL-02 frontend half)** - `7832865d` (test)

_Plan-metadata commit (this SUMMARY/STATE/ROADMAP) follows below._

## Files Created/Modified
- `app/src/routes/admin/+page.server.ts` — added `env` import from `$env/dynamic/private` (with an inline comment naming D-07 so a future reader doesn't "normalize" it back to the static import), `isDevelopment` in the load return, `RESET_ENV_ERROR`/`RESET_MID_ERROR` constants, and `actions.resetToFixture`
- `app/src/routes/admin/+page.svelte` — added `enhance`/`invalidateAll` imports, `form` destructured alongside `data`, `resetConfirming`/`resetRunning`/`resetResult` `$state`, the full Dev Tools section markup, and a `<style>` block with `@keyframes spin`
- `tests/test_admin_dev_frontend_gate.py` — new file: `test_dev_tools_section_is_server_gated`, `test_environment_not_client_exposed`, `test_reset_action_posts_no_operator_input`, `test_error_copies_match_ui_spec`

## Decisions Made
- `ENVIRONMENT` is read through `$env/dynamic/private`, never `$env/static/private` — the static import (used elsewhere in this same file for `ADMIN_TOKEN`/`FASTAPI_BASE_URL`) is inlined by Vite at build time, which would silently turn the Dev Tools gate into a build-time decision requiring separate prod/dev build artifacts. D-07 requires one codebase, gate evaluated at request time.
- `resetToFixture` does not `redirect()` on success (every other `/admin` action does) — it returns `{ resetFixtures: body.fixtures }` directly so the UI-SPEC's Success state can render inline on the same page without a navigation.
- A parsed `fixtures` array with anything other than exactly 4 entries is routed to the mid-reset error path, not a shorter success list — matches the UI-SPEC's explicit "partial" resolution (no "2 of 4 reseeded" state exists to design or render).
- Did **not** mark DEVTOOL-01/DEVTOOL-02 complete in `REQUIREMENTS.md`, though this plan's frontmatter lists both. Plan 43-04 closes both requirements by actually attempting the production-refusal case (view-source confirming the section's absence, plus a direct 404 against the reset endpoint) — flipping the checkboxes before that live demonstration runs would misstate phase status, mirroring 43-01-SUMMARY's and 43-02-SUMMARY's identical reasoning for this same phase.
- `test_reset_action_posts_no_operator_input` isolates the `resetToFixture` action's own body (via a string slice starting at `"resetToFixture:"`) before asserting no `request.formData()`/`corpus_dir` reference, so a match in a different action earlier in the same file could never produce a false pass.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug/Test design] Duplicate literal string broke exact-match acceptance criteria and the new test's uniqueness assertion**
- **Found during:** Task 1's acceptance-criteria verification (`grep -c '\$env/dynamic/private'` returned 2, not the plan's required 1) and again during Task 3 (the new test's own `heading_count == 1` assertion failed because "Dev Tools" appeared twice — once in the heading, once in an explanatory code comment)
- **Issue:** Explanatory inline comments I wrote for the D-07 deviation (in `+page.server.ts`) and for the Dev Tools `$state` block (in `+page.svelte`) happened to repeat the exact literal strings (`$env/dynamic/private`, `Dev Tools`) that the plan's grep-based acceptance criteria and Task 3's own test assert appear exactly once — a correct, intentional design choice in both the plan and the test, not a bug in either.
- **Fix:** Reworded both comments to preserve their explanatory content without repeating the exact literal substring a second time (e.g. "the dynamic-private env module below" instead of restating the full import path; "Dev-tools" instead of "Dev Tools" in the state-block comment).
- **Files modified:** `app/src/routes/admin/+page.server.ts`, `app/src/routes/admin/+page.svelte`
- **Verification:** Re-ran all Task 1/Task 2 grep-based acceptance criteria (all pass) and `tests/test_admin_dev_frontend_gate.py` (4/4 pass) after the wording change; `npm run check` re-confirmed 0 errors.
- **Committed in:** `6c533cc3` (Task 1's comment) and split across `6465b893`/`7832865d` (Task 2's comment, tweaked again in the Task 3 commit once the test caught the second duplicate)

**2. [Rule 3 - Blocking issue] Precondition on `app/.env` could not be verified by this executor's own tools**
- **Found during:** Task 1's mandatory precondition check, before any code was written
- **Issue:** Task 1's `<precondition>` required confirming `app/.env` contains `ENVIRONMENT=development` — this session's sandbox permission settings deny all `Read`/`Bash` access to any `.env`-pattern file (a deliberate secrets-protection boundary, since `app/.env` also holds `ADMIN_TOKEN`/`FASTAPI_BASE_URL`), so this could not be verified via the mandated read-only checks. The precondition's second half (a live `curl -X POST` against the real reset endpoint) was also not run as written, since that call is genuinely destructive and the protocol forbids side-effecting verification checks.
- **Fix:** Verified backend reachability non-destructively instead, via the existing automated test suite (`api/tests/test_admin_dev_routes.py` + `tests/test_admin_dev_router_gate.py`, 14/14 passing) rather than a live curl. For the `.env` half, halted and returned a `checkpoint:human-action` per the precondition protocol (unmet preconditions are never auto-approved). The coordinator subsequently relayed the project owner's direct confirmation that `app/.env` already contains `ENVIRONMENT=development`, resolving the checkpoint through the normal parent-orchestrator channel.
- **Files modified:** none (verification-only; no code changed as a result of this deviation)
- **Verification:** `./.venv/Scripts/python.exe -m pytest api/tests/test_admin_dev_routes.py tests/test_admin_dev_router_gate.py -q` — 14 passed, before Task 1's code was written.
- **Committed in:** n/a (no code change — a process/verification deviation only)

---

**Total deviations:** 2, both Rule 1/3 (test-technique and verification-process adjustments discovered while executing the plan's own acceptance criteria/precondition, not implementation defects). No scope creep — both were necessary to make the plan's own verification actually work as intended, and neither altered the shipped behavior.

## Issues Encountered

None beyond the two deviations above, both resolved before their respective commits.

## User Setup Required

None for this plan specifically. `app/.env`'s `ENVIRONMENT=development` (flagged as outstanding by 43-01-SUMMARY and 43-02-SUMMARY) was confirmed present by the project owner during this plan's execution — see Deviation 2 above.

## Next Phase Readiness
- The frontend half of DEVTOOL-01/DEVTOOL-02 is now feature-complete: `/admin` in development shows the Dev Tools section with the DEV ONLY badge, the two-step confirm states the full wipe scope, Running/Success/Error all match the UI-SPEC, and the environment value never reaches the browser. Plan 43-04 (live UAT) can now exercise this end-to-end against a real dev environment.
- Plan 43-04's Task 2 ("Prove the production refusal by actually attempting it") is the natural place to flip `ENVIRONMENT` to a non-development value and confirm both halves of D-07 together: the backend 404s (already proven at the unit level by Plan 43-01) and `/admin`'s served HTML contains no Dev Tools section at all (view-source, not just visual absence) — this plan's `test_dev_tools_section_is_server_gated` proves the source-level mechanism but a live view-source check is the remaining manual confirmation, per 43-VALIDATION.md's accepted fallback.
- DEVTOOL-01/DEVTOOL-02 remain unchecked in `REQUIREMENTS.md`, intentionally, pending Plan 43-04's live production-refusal demonstration.

## Self-Check: PASSED

Confirmed all created/modified files exist on disk with the expected content: `app/src/routes/admin/+page.server.ts` contains `isDevelopment`, `resetToFixture`, and both locked error copies; `app/src/routes/admin/+page.svelte` contains the Dev Tools section gated by `{#if data.isDevelopment}` with `@keyframes spin`; `tests/test_admin_dev_frontend_gate.py` exists with 4 test functions. All three task commit hashes (`6c533cc3`, `6465b893`, `7832865d`) confirmed present in `git log --oneline --all`. `cd app && npm run check` (804 files, 0 errors) and `./.venv/Scripts/python.exe -m pytest -q` (841 passed, 5 xfailed, 4 pre-existing unrelated errors) both re-confirmed against the final committed state.

---
*Phase: 43-dev-only-reset-to-fixture*
*Completed: 2026-07-31*
