---
phase: 51-design-system-noun-alignment
plan: 08
subsystem: ui
tags: [sveltekit, svelte5, fastapi, pytest, term-grouped-listing, d-16-variant-a]

requires:
  - phase: 51-design-system-noun-alignment
    provides: "plan 51-04's GET /arguments/terms and GET /arguments/term/{term_year} endpoints; plan 51-06's Button/Card primitives and @lucide/svelte; plan 51-07's token-converted lib/public/ pattern"
provides:
  - "app/src/routes/arguments/+page.server.ts + +page.svelte — the /arguments term index (D-14)"
  - "app/src/routes/arguments/term/[year]/+page.server.ts + +page.svelte — the /arguments/term/{year} term detail (D-14/D-16)"
  - "app/src/lib/public/TermRow.svelte — D-16 Variant A's three-field row"
  - "app/src/lib/formatting.ts — shared formatDate + formatArgumentCount helpers"
  - "api/routers/cases.py, api/services/cases.py, api/schemas/cases.py deleted; GET /cases returns 404"
affects: [51-09-token-sweep, 51-10-inventory]

actuals:
  tokens: 22847
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Route-tree +error.svelte as the mechanism for rendering copywriting-contract error text with no leaked HTTP status number — SvelteKit's default fallback error page renders the raw status code, which the Copywriting Contract forbids."
    - "Guarantee migration on deletion: every source-level/behavioral assertion a retired module's tests carried is retargeted onto its replacement function BEFORE the old test is deleted, in the same commit — never delete a test and its guarantee together."

key-files:
  created:
    - app/src/lib/formatting.ts
    - app/src/routes/arguments/+error.svelte
    - app/src/routes/arguments/term/[year]/+page.server.ts
    - app/src/routes/arguments/term/[year]/+page.svelte
    - app/src/lib/public/TermRow.svelte
    - app/tests/arguments-listing.browser.test.mjs
    - api/tests/test_argument_list_item_argued_date_optional.py
  modified:
    - app/src/routes/arguments/+page.server.ts
    - app/src/routes/arguments/+page.svelte
    - api/main.py
    - api/routers/admin.py
    - api/schemas/admin_arguments.py
    - api/services/arguments.py
    - api/tests/test_arguments.py
    - api/tests/test_public_arguments_listing.py
    - api/tests/test_published_gate.py
    - api/tests/test_question_number_nullable.py
    - api/tests/test_trust_public_leak_ban.py
    - tests/test_admin_dev_router_gate.py
    - tests/test_admin_router.py

key-decisions:
  - "D-16 Variant A shipped exactly as the operator locked it in 51-DESIGN-DECISIONS.md — TermRow.svelte carries case name, argued date, docket number only. No advocate line, no argument_participants -> people join. The plan text itself was already written against Variant A (no Variant B ambiguity survived into 51-08-PLAN.md), so this is not a reduction from what the plan asked for."
  - "Added app/src/routes/arguments/+error.svelte (not in the plan's files_modified list) — Rule 2, missing critical functionality. SvelteKit's built-in fallback error page renders the raw HTTP status code in its heading, which the Copywriting Contract's error-state string explicitly forbids surfacing. A route-tree error boundary was the only way to satisfy 'no HTTP status number, no error detail' for a non-OK upstream fetch."
  - "Renamed api/tests/test_case_item_argued_date_optional.py to test_argument_list_item_argued_date_optional.py per the plan's explicit instruction to rename any retargeted test whose name still says CaseItem, once its assertions moved onto ArgumentListItem."

requirements-completed: [DS-01, DS-04]

coverage:
  - id: D1
    description: "/arguments term index renders one row per term with published-argument count, empty state, and error state per the Copywriting Contract"
    requirement: "DS-04"
    verification: []
    human_judgment: true
    rationale: "Verified server-render correctness (200/rows/hrefs/empty-copy/error-copy/singular-plural) via a one-off curl-against-vite+mock-API harness during execution — not a committed automated test. The committed browser test (arguments-listing.browser.test.mjs) covers this but is unrun in this environment (no Chromium/Edge binary). Real-browser confirmation (viewport scroll at 375px/1280px with ~65 rows) is an operator-UAT item."
  - id: D2
    description: "/arguments/term/{year} term detail lists a term's published arguments in D-16 Variant A's row shape, distinguishes a real-but-empty term (200) from a bad year (404), and links each row to /arguments/{slug}"
    requirement: "DS-04"
    verification: []
    human_judgment: true
    rationale: "Verified server-render correctness for all four cases (populated 200, empty-term 200, non-numeric-year 404, out-of-range-year 404) via the same one-off curl harness. Real-browser confirmation (a ~150-row term at both viewports, long case-name wrap with docket staying visible) is an operator-UAT item; the browser test covering the click-through paths is unrun for the same reason as D1."
  - id: D3
    description: "app/tests/arguments-listing.browser.test.mjs — first real-browser coverage of the public listing, six test cases"
    verification: []
    human_judgment: true
    rationale: "Written per the plan's instruction but genuinely unrun — no Chromium/Edge binary exists in this environment (confirmed: 'Microsoft Edge or Google Chrome must be installed for this fail-closed test' assertion fails closed, same as the four pre-existing browser tests). Operator must run `node --test app/tests/arguments-listing.browser.test.mjs` on a machine with a browser installed."
  - id: D4
    description: "The /cases API surface (router, service, schema) is deleted, GET /cases 404s, and every guarantee its tests carried is asserted against its replacement rather than dropped"
    requirement: "DS-01"
    verification:
      - kind: integration
        ref: "pytest -q (bare invocation, full suite)"
        status: pass
      - kind: integration
        ref: "api/tests/test_public_arguments_listing.py -q -rs (17 passed, 0 skipped)"
        status: pass
      - kind: integration
        ref: "api/tests/test_trust_public_leak_ban.py -q (110 passed)"
        status: pass
      - kind: other
        ref: "GET /cases via ASGITransport client -> 404"
        status: pass
    human_judgment: false
---

# Phase 51 Plan 08: Arguments Listing (Term Index + Term Detail) and /cases Retirement Summary

**The `/arguments` term index and `/arguments/term/{year}` term detail (D-16 Variant A's three-field row) replace the transitional flat listing, and the `/cases` API surface — router, service, schema — is deleted with every one of its tests' guarantees migrated onto the term-grouped replacement rather than dropped.**

## Performance

- **Duration:** ~66 min
- **Started:** 2026-08-28T18:12:33Z (approximate — phase 51-07 completed at this timestamp; this plan began shortly after)
- **Completed:** 2026-08-28T19:18:50Z
- **Tasks:** 3
- **Files modified:** 26 (7 created, 13 modified, 6 deleted/renamed)

## Accomplishments

- `/arguments` is now the term index: one row per October Term carrying a published-argument count, term identifier primary / count secondary per the UI-SPEC focal points, exact Copywriting Contract empty and error copy, no CTA (a row is the action).
- `/arguments/term/{year}` is the term detail: D-16 Variant A's locked three-field `TermRow` (case name, argued date, docket number), a genuine 404 for a bad/out-of-range year vs. a 200 term-scoped empty state for a real-but-empty term, all rows on one page (no pagination).
- `app/src/lib/formatting.ts` — one shared `formatDate`/`formatArgumentCount` definition site used by both listing routes.
- `app/src/routes/arguments/+error.svelte` (Rule 2 addition) — renders the Copywriting Contract's exact error string with no HTTP status number or error detail, while still 404ing genuinely for a bad slug/year.
- `app/tests/arguments-listing.browser.test.mjs` — the first real-browser test for the public listing, six test cases sharing one vite+browser session; written per the plan, unrun in this environment (no Chromium/Edge binary — fails closed on its own presence assertion, same as the four pre-existing browser tests).
- `/cases` API surface (`api/routers/cases.py`, `api/services/cases.py`, `api/schemas/cases.py`) deleted along with its `api/main.py` registration. Every live guarantee its tests carried has a named new home (see Deviations / Task 3 detail below) — none were dropped.
- Bare `pytest -q`: **1348 passed, 5 xfailed, 0 failed** (full suite, run twice after Task 3's edits). `npm --prefix app run check`: 0 errors, 33 pre-existing warnings (baseline unchanged). `npm --prefix app run build`: exits 0.

## Task Commits

1. **Task 1: `/arguments` term index** — `0496e1719` (feat)
2. **Task 2: `/arguments/term/[year]` and `TermRow.svelte`** — `ef5af95fa` (feat)
3. **Task 3: Retire the `/cases` API surface with its last consumer** — `0bf9c9fba` (feat)

**Plan metadata:** commit pending (this SUMMARY + STATE.md + ROADMAP.md progress update)

## Files Created/Modified

- `app/src/lib/formatting.ts` — shared `formatDate` + `formatArgumentCount` (singular/plural) helpers
- `app/src/routes/arguments/+page.server.ts` — now fetches `GET /arguments/terms`, fails closed
- `app/src/routes/arguments/+page.svelte` — term index rows, empty state
- `app/src/routes/arguments/+error.svelte` — route-tree error boundary (Rule 2 addition)
- `app/src/routes/arguments/term/[year]/+page.server.ts` — fetches `GET /arguments/term/{year}`, 422->404 mapping, real-empty-term 200
- `app/src/routes/arguments/term/[year]/+page.svelte` — term detail heading + rows + term-scoped empty state
- `app/src/lib/public/TermRow.svelte` — D-16 Variant A row component
- `app/tests/arguments-listing.browser.test.mjs` — 6-case real-browser test (unrun, see D3 above)
- `api/main.py` — `cases_router` import/registration removed
- `api/routers/admin.py` — stale comment naming the retired read path corrected
- `api/schemas/admin_arguments.py` — stale comment naming the retired module corrected
- `api/services/arguments.py` — stale docstring reference to the retired endpoint corrected
- `api/tests/test_arguments.py` — `test_cases_list_never_leaks_trust_tier` removed, comment block updated
- `api/tests/test_public_arguments_listing.py` — unpublish-invisibility test folded in (4 read paths, was 3)
- `api/tests/test_published_gate.py` — `TestPublishedGate` class removed; two EDGE tests retargeted onto `list_arguments_for_term`
- `api/tests/test_question_number_nullable.py` — retargeted onto `ArgumentListItem`
- `api/tests/test_trust_public_leak_ban.py` — router/schema module lists updated, `PUBLIC_FRONTEND_PATHS` swapped, new `PUBLIC_FASTAPI_BASE_URL` sweep test added
- `tests/test_admin_dev_router_gate.py` — `/cases` mount assertion replaced with an `/arguments/term` sub-path assertion
- `tests/test_admin_router.py` — `cases_router` presence check flipped to an absence check (consumer found by the mandated whole-repo grep, not named in the plan's own read_first list)
- `api/tests/test_argument_list_item_argued_date_optional.py` — renamed from `test_case_item_argued_date_optional.py`, retargeted onto `ArgumentListItem`

**Deleted:** `api/routers/cases.py`, `api/services/cases.py`, `api/schemas/cases.py`, `tests/test_cases_api.py`, `api/tests/test_phase48_unpublish_visibility.py`

## Decisions Made

- D-16 Variant A shipped exactly as locked — see frontmatter `key-decisions`.
- The `app/src/routes/arguments/+error.svelte` addition (Rule 2) — see frontmatter `key-decisions`.
- The `test_case_item_argued_date_optional.py` rename — see frontmatter `key-decisions`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added `app/src/routes/arguments/+error.svelte`**
- **Found during:** Task 1
- **Issue:** The plan's Copywriting Contract requires the generic listing error ("Unable to load arguments right now. Try refreshing the page.") to render with no HTTP status number and no error detail reaching the page. SvelteKit's built-in fallback error page renders the raw status code in its `<h1>` when no route-tree `+error.svelte` exists, which would violate that contract on every non-OK upstream fetch.
- **Fix:** Added a shared `+error.svelte` for the `/arguments` route tree that renders the exact contract string for any non-404 status, and a minimal genuine 404 (no leaked detail) for status 404 — verified via a curl-against-vite harness that a simulated 500 produces neither the substring `500` nor `Error:` in the rendered HTML.
- **Files modified:** `app/src/routes/arguments/+error.svelte`
- **Verification:** Curl harness (throwaway script, not committed) confirmed the exact contract string renders and neither `500` nor `Error:` appears in the response body for a simulated upstream 500; a simulated bad year/slug still returns HTTP 404.
- **Committed in:** `0496e1719` (Task 1 commit)

**2. [Rule 1 - Bug / missed consumer] Fixed `tests/test_admin_router.py::test_main_py_still_registers_all_existing_routers` asserting `cases_router` presence**
- **Found during:** Task 3, via the bare `pytest -q` full-suite run (not via the plan's own read_first grep list — this consumer checks for the string `"cases_router"`, which none of the plan's mandated grep patterns match, exactly the class of miss the plan's Task 3 hazard note warns about)
- **Issue:** This pre-existing regression guard asserted `api/main.py` still registers `cases_router`, which Task 3 deliberately removes. Left unfixed, it would fail the whole suite.
- **Fix:** Flipped the assertion to require `cases_router` is ABSENT from `api/main.py`, with a docstring explaining the deliberate removal (D-14's original regression-prevention intent — don't accidentally drop a router — still holds for `arguments_router`/`people_router`).
- **Files modified:** `tests/test_admin_router.py`
- **Verification:** Bare `pytest -q` — 1348 passed, 5 xfailed, 0 failed.
- **Committed in:** `0bf9c9fba` (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (1 missing critical, 1 bug/missed consumer).
**Impact on plan:** Both fixes were necessary for correctness — the first to satisfy the Copywriting Contract's information-disclosure constraint (T-51-08-01), the second to keep the full suite green after a deliberate, plan-mandated deletion. No scope creep beyond what Task 3's own hazard note anticipated ("a deletion that breaks a consumer you did not find will surface as a red test").

## Guarantee Migration Ledger (Task 3)

Every guarantee a deleted test carried, and where it now lives:

| Retired guarantee | Retired test/module | New home |
|---|---|---|
| Consolidated-docket `is_lead` filter | `tests/test_cases_api.py::test_is_lead_filter_in_cases_service` | Proven behaviorally by `api/tests/test_public_arguments_listing.py::test_terms_consolidated_docket_contributes_one` and `::test_term_detail_consolidated_docket_contributes_one_row` (already existed, added by plan 51-04) |
| `Base.metadata.create_all` ban | `tests/test_cases_api.py::test_no_create_all_in_cases_router` / `::test_no_create_all_in_cases_service` | Already covered repo-wide by `tests/test_schema.py::test_no_create_all_in_codebase` (sweeps `api/`, `alembic/`, `pipeline/` recursively) — confirmed before relying on it |
| Server-only `FASTAPI_BASE_URL` (no `PUBLIC_` prefix) | `tests/test_cases_api.py::test_no_public_fastapi_base_url_in_cases_pages` | New `api/tests/test_trust_public_leak_ban.py::test_public_frontend_pages_never_use_public_fastapi_base_url`, retargeted onto `PUBLIC_FRONTEND_PATHS` |
| `published_at` gate + return-shape source assertions | `api/tests/test_published_gate.py::TestPublishedGate` (4 tests) | `TestTermGroupedListingPublishedGate` (pre-existing, added by plan 51-04) is now the sole carrier; two `TestArgumentDetailPublishedGate` EDGE tests retargeted from `get_cases()` onto `list_arguments_for_term()` |
| Unpublish invisibility across all public read paths | `api/tests/test_phase48_unpublish_visibility.py` (deleted, phase-numbered) | Folded into `api/tests/test_public_arguments_listing.py::test_unpublished_argument_is_absent_from_all_public_read_paths`, now checking 4 read paths (`list_terms`, `list_arguments_for_term`, `get_argument_with_utterances`, `get_argument_speakers`) instead of 3 |
| Live trust-tier leak-ban half over the flat listing | `api/tests/test_arguments.py::test_cases_list_never_leaks_trust_tier` | `api/tests/test_public_arguments_listing.py`'s three live leak assertions over `GET /arguments/terms`, `GET /arguments/term/{term_year}`, `GET /arguments/by-slug/{slug}/utterances` (added by plan 51-04, confirmed to run — 0 skipped) |
| `/cases` router mount regression guard | `tests/test_admin_dev_router_gate.py::_assert_pre_existing_routers_still_mounted`'s `/cases` assertion | Replaced with an `/arguments/term` sub-path assertion (2 `assert ... startswith("/arguments` lines total, up from 1) |
| `cases_router` registration guard (found via whole-suite run, not the plan's grep list) | `tests/test_admin_router.py::test_main_py_still_registers_all_existing_routers` | Same test, flipped to assert absence — see Deviation 2 above |
| `CaseItem.argued_date`/`.question_number` nullable-column regression | `api/tests/test_case_item_argued_date_optional.py`, `api/tests/test_question_number_nullable.py`'s `CaseItem` test | Retargeted onto `ArgumentListItem` (renamed the first file; edited the second in place) |

## Issues Encountered

None beyond the two deviations documented above.

## User Setup Required

None — no external service configuration required.

## Operator UAT Items (browser unavailable in this environment)

1. Run `node --test app/tests/arguments-listing.browser.test.mjs` on a machine with Chromium or Microsoft Edge installed — confirm all 6 test cases pass.
2. View `/arguments` at 375px and 1280px with the full corpus (~65 terms) — confirm it scrolls cleanly with no pagination control.
3. View `/arguments/term/{year}` for a term populated to ~150 rows at both viewports — confirm a long consolidated case name wraps and its docket number stays visible at 375px.
4. Confirm the D-16 Variant A row visually matches the operator's chosen row in the Figma `d16-comparison` frame (no Figma MCP access in this environment — see "MCP substitution" below).

## MCP Substitution

The plan's required reading listed a Figma MCP check; `ToolSearch` was disabled in this session so the Figma MCP tools were unreachable. The design contract was instead read entirely from `51-DESIGN-DECISIONS.md`'s "Term-row variant (D-16)" section (Variant A, operator-locked) and `51-UI-SPEC.md`'s focal-points/Copywriting Contract tables, both on disk. No Figma-only detail was needed beyond what these two documents already record.

## Next Phase Readiness

- The public arguments listing IA (D-14) and row shape (D-16 Variant A) are complete; DS-04 is satisfied for the listing style decision and implementation.
- DS-01's API-side noun alignment is complete — `/cases` no longer exists anywhere in the stack (frontend routes were retired in plan 51-02; the API surface is retired here).
- Remaining Phase 51 work (per STATE.md/ROADMAP.md): plan 51-09 (token sweep) and plan 51-10 (phase-wide inventory) are unaffected by this plan's scope and can proceed independently.
- The real-browser test this plan adds needs to be run in a browser-capable environment before Phase 51 verification can close DS-04 with full confidence — flagged above as an Operator UAT item, not silently marked passing.

---
*Phase: 51-design-system-noun-alignment*
*Completed: 2026-08-28*

## Self-Check: PASSED

- `app/src/lib/formatting.ts` — FOUND
- `app/src/routes/arguments/+error.svelte` — FOUND
- `app/src/routes/arguments/term/[year]/+page.server.ts` — FOUND
- `app/src/routes/arguments/term/[year]/+page.svelte` — FOUND
- `app/src/lib/public/TermRow.svelte` — FOUND
- `app/tests/arguments-listing.browser.test.mjs` — FOUND
- `api/tests/test_argument_list_item_argued_date_optional.py` — FOUND
- `api/routers/cases.py`, `api/services/cases.py`, `api/schemas/cases.py`, `tests/test_cases_api.py`, `api/tests/test_phase48_unpublish_visibility.py` — CONFIRMED ABSENT
- Commits `0496e1719`, `ef5af95fa`, `0bf9c9fba` — FOUND in `git log --oneline`
- All Task 1-3 acceptance criteria re-run and confirmed passing (see body above); bare `pytest -q` re-run after all changes: 1348 passed, 5 xfailed, 0 failed.
