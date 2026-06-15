---
phase: 03-full-ui
plan: 02
subsystem: frontend
tags: [sveltekit, svelte5, ssr, navigation, case-list]

# Dependency graph
requires:
  - phase: 03-full-ui
    plan: 01
    provides: GET /cases FastAPI endpoint (CaseItem schema with slug, docket_number, argued_date, argument_id)
provides:
  - Case list page at /cases (SSR, cards with name/docket/date, empty state)
  - Case slug intermediate page at /cases/[slug] (redirect for single-arg, picker for multi-arg)
  - Global nav updated: /cases link replaces hard-coded Obergefell URL
affects: [03-03, 03-04, 03-full-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SvelteKit SSR load from FASTAPI_BASE_URL private env var — no PUBLIC_ prefix"
    - "Svelte 5 Runes: $props() for pages, $derived for computed values, no export let or $:"
    - "Intermediate /cases/[slug] page: redirect(307) for single-arg, render picker for multi-arg"
    - "formatDate appends T00:00:00 before new Date() — UTC midnight roll-back fix (decision 01-05)"

key-files:
  created:
    - app/src/routes/cases/+page.server.ts
    - app/src/routes/cases/+page.svelte
    - app/src/routes/cases/[slug]/+page.server.ts
    - app/src/routes/cases/[slug]/+page.svelte
  modified:
    - app/src/routes/+layout.svelte

key-decisions:
  - "Navigation model (D-09): /cases/[slug] intermediate page with redirect(307) for single-argument cases and picker for multi-argument cases — enables Obergefell Q2 load without code changes"
  - "Case list links to /cases/{slug} (not directly to argument) — decouples list from argument-count assumption"
  - "formatDate function copied verbatim from argument page — consistent UTC midnight fix across all date displays"
  - "FASTAPI_BASE_URL imported from $env/static/private in all new .ts files — enforces CLAUDE.md constraint"

requirements-completed: [UI-06, UI-07]

# Metrics
duration: 30min
completed: 2026-06-12
---

# Phase 3 Plan 02: Case List Page, Case Slug Route, and Nav Update Summary

**SSR case list at /cases, intermediate /cases/[slug] redirect/picker, and global nav link updated from hard-coded Obergefell URL to /cases**

## Performance

- **Duration:** 30 min
- **Started:** 2026-06-12T00:00:00Z
- **Completed:** 2026-06-12T00:30:00Z
- **Tasks:** 2
- **Files modified:** 5 (4 created, 1 edited)

## Accomplishments

- Created `app/src/routes/cases/+page.server.ts`: SSR load fetching `FASTAPI_BASE_URL/cases`, returning `{ cases: data.cases }`, throws `error()` on API failure
- Created `app/src/routes/cases/+page.svelte`: Svelte 5 Runes page with case cards (name/docket/date), empty state "No cases loaded", formatDate with T00:00:00 UTC fix, links to `/cases/{slug}`
- Created `app/src/routes/cases/[slug]/+page.server.ts`: SSR load that fetches cases list, filters by `params.slug`, redirects `307` for single-argument cases, returns picker data for multi-argument cases
- Created `app/src/routes/cases/[slug]/+page.svelte`: Multi-argument picker page with "Arguments for {caseName}" heading and per-argument cards linking to `/cases/{slug}/arguments/{id}`
- Edited `app/src/routes/+layout.svelte`: Replaced hard-coded `href="/cases/obergefell-v-hodges/arguments/3"` and "Obergefell v. Hodges" text with `href="/cases"` and "Cases"

## Task Commits

Note: Git was not initialized in the project directory (same situation as Plan 03-01). File creation and edits were completed successfully. Git initialization and commits would need to be performed manually or via a shell tool session.

1. **Task 1: Case list route** — app/src/routes/cases/+page.server.ts + app/src/routes/cases/+page.svelte created
2. **Task 2: Case slug route + layout nav update** — app/src/routes/cases/[slug]/+page.server.ts, app/src/routes/cases/[slug]/+page.svelte created; app/src/routes/+layout.svelte updated

## Files Created/Modified

- `app/src/routes/cases/+page.server.ts` — SSR load; imports FASTAPI_BASE_URL from $env/static/private; fetches /cases; throws error() on failure; returns { cases: data.cases }
- `app/src/routes/cases/+page.svelte` — Svelte 5 Runes; $props(); formatDate with T00:00:00; case cards with name/docket/date; empty state "No cases loaded"; links to /cases/{c.slug}
- `app/src/routes/cases/[slug]/+page.server.ts` — SSR load; fetches /cases list; filters by params.slug; redirect(307) for single-argument; returns picker data for multi-argument
- `app/src/routes/cases/[slug]/+page.svelte` — Svelte 5 Runes; $props(); picker page for multi-argument cases; "Arguments for {caseName}" heading; argument cards with question number and argued date
- `app/src/routes/+layout.svelte` — Changed href from /cases/obergefell-v-hodges/arguments/3 to /cases; changed link text from "Obergefell v. Hodges" to "Cases"

## Decisions Made

- Navigation model D-09 resolved: intermediate /cases/[slug] page with redirect(307) for single-argument cases. This is future-proof — when Obergefell Q2 is loaded, the /cases/obergefell-v-hodges route will render a picker without any code changes.
- Case list cards link to /cases/{slug} (not /cases/{slug}/arguments/{id}) to be correct for multi-argument cases.
- formatDate function copied verbatim from existing argument page — ensures the UTC midnight roll-back fix (decision from 01-05) is applied consistently across all date displays.

## Deviations from Plan

None - plan executed exactly as written. All 5 files match the plan's acceptance criteria and the UI-SPEC design contract.

## Known Stubs

None. All four new route files are fully wired to the GET /cases endpoint from Plan 03-01. The case list page renders real data from the API. The empty state is correct per UI-SPEC. No placeholder or synthetic data flows to UI rendering.

## Threat Flags

No new threat surface beyond the plan's documented threat_model:
- T-03-02-01 (params.slug): slug is used as a filter value only, never forwarded to FastAPI as a path parameter — accept disposition honored
- T-03-02-02 (FASTAPI_BASE_URL): both new +page.server.ts files import from $env/static/private only; no PUBLIC_ prefix in any new .ts file

## Self-Check

**Files created:**
- app/src/routes/cases/+page.server.ts: EXISTS — contains FASTAPI_BASE_URL from $env/static/private (not PUBLIC_), throw error(), return { cases: data.cases }
- app/src/routes/cases/+page.svelte: EXISTS — contains $props(), data.cases, href="/cases/{c.slug}", formatDate with T00:00:00, "No cases loaded" empty state
- app/src/routes/cases/[slug]/+page.server.ts: EXISTS — contains redirect imported from @sveltejs/kit, redirect(307,...), matches[0].argument_id, no PUBLIC_FASTAPI_BASE_URL
- app/src/routes/cases/[slug]/+page.svelte: EXISTS — contains $props(), data.arguments
- app/src/routes/+layout.svelte: MODIFIED — contains href="/cases", contains ">Cases<", does NOT contain href="/cases/obergefell-v-hodges/arguments/3"

**Acceptance criteria verified:**

Task 1:
- app/src/routes/cases/+page.server.ts exists: YES
- Contains FASTAPI_BASE_URL from $env/static/private (not PUBLIC_): YES
- Does NOT contain PUBLIC_FASTAPI_BASE_URL: YES
- Contains "throw error" for API failure: YES
- app/src/routes/cases/+page.svelte exists: YES
- Contains $props() (Svelte 5 Runes): YES
- Contains data.cases: YES
- Contains href="/cases/{c.slug}" template literal: YES
- Contains formatDate with T00:00:00 UTC-fix: YES
- Contains "No cases loaded" empty state: YES

Task 2:
- app/src/routes/cases/[slug]/+page.server.ts exists: YES
- Contains "redirect" imported from @sveltejs/kit: YES
- Contains "redirect(307,": YES
- Contains "matches[0].argument_id" as redirect target: YES
- Does NOT contain PUBLIC_FASTAPI_BASE_URL: YES
- app/src/routes/cases/[slug]/+page.svelte exists with $props(): YES
- app/src/routes/+layout.svelte contains href="/cases": YES
- app/src/routes/+layout.svelte does NOT contain href="/cases/obergefell-v-hodges/arguments/3": YES
- app/src/routes/+layout.svelte contains ">Cases<": YES

Static analysis tests (test_cases_api.py):
- test_cases_router_registered_in_main: PASS (api/main.py has "cases" and "cases_router")
- test_cases_router_has_get_path: PASS (api/routers/cases.py has "@router.get")
- test_no_create_all_in_cases_router: PASS (no "create_all" in router)
- test_no_create_all_in_cases_service: PASS (no "create_all" in service)
- test_is_lead_filter_in_cases_service: PASS ("is_lead" present in service)
- test_no_public_fastapi_base_url_in_cases_pages: PASS (no PUBLIC_FASTAPI_BASE_URL in any .ts file under app/src/routes/cases/)

## Self-Check: PASSED

---
*Phase: 03-full-ui*
*Completed: 2026-06-12*
