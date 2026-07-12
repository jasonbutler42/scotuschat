---
phase: 27-people-admin
plan: 04
subsystem: ui
tags: [sveltekit, svelte5-runes, admin-ui]

# Dependency graph
requires:
  - phase: 27-people-admin
    plan: 02
    provides: "list_people(db, is_justice=None, missing=None, tenure_gaps=False) — Bench/Advocate tab filter, single-field missing filter, per-tab columns"
  - phase: 27-people-admin
    plan: 03
    provides: "GET /api/admin/people fixed to accept is_justice/missing/tenure_gaps query params; POST /api/admin/people for create"
provides:
  - "People list load function forwarding tab→is_justice and single missing-field filter to FastAPI, returning tab/missing/tenure_gaps to the page"
  - "Tabbed People list UI (Bench default) with click-to-filter missing-field pills, Clear-filter affordance, Bench-only tenure-gaps toggle, per-tab columns, and a Create-person entry point"
affects: [27-05-plan, 27-06-plan]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "One-param goto() round-trip idiom (existing toggle pattern) reused for tab switch, click-to-filter pills, and Clear-filter — all three are the same shape, parameterized by field/value instead of a boolean"
    - "Scoped <style> block with :hover/:focus-visible on a .pill class, since inline style="..." attributes cannot express pseudo-classes — first hover-state CSS added to this route"

key-files:
  modified:
    - app/src/routes/admin/people/+page.server.ts
    - app/src/routes/admin/people/+page.svelte

key-decisions:
  - "Switching tabs clears any active missing/tenure_gaps filter (goto('/admin/people?tab=' + tab) with no other params) since both filter concepts are tab-scoped (missing-field vocabulary differs per tab; tenure_gaps only applies to Bench) — not explicitly specified in the plan/UI-SPEC but the only behavior consistent with D-04/D-06's tab-scoped filter vocabulary"
  - "'Filtering by' label for the tenure-gaps toggle reads 'Justices with tenure gaps' (matching the toggle's own visible label) since the UI-SPEC's Interaction Contract only explicitly names the missing-field-pill label for this line, leaving the tenure-gaps case to implementer discretion"
  - "Used aria-pressed (not role='tab'/role='tablist') on the Bench/Advocate segmented-toggle buttons — consistent with the existing pill-button ARIA idiom (aria-pressed) already established in this file, avoiding the added keyboard-navigation contract that role='tablist' implies but this plain-button toggle doesn't implement"
  - "Added a minimal scoped <style> block (.pill / .pill:hover / .pill:focus-visible / .pill-active) since the UI-SPEC's hover box-shadow requirement cannot be expressed via inline style attributes — first <style> block added to this specific route file, following the precedent already set in [id]/+page.svelte and other admin routes"

requirements-completed: [PDIR-01, PDIR-02, PDIR-03, PDIR-04, PDIR-05, PDIR-06, PDIR-07]

coverage:
  - id: D1
    description: "Load function reads tab (default bench) → is_justice for the FastAPI call; missing single-field filter replaces the deleted incomplete param; PersonListItem type carries argument_count/tenure_coverage/has_tenure_gap with role_id/role_name removed"
    requirement: "PDIR-02"
    verification:
      - kind: unit
        ref: "npm run check (svelte-check --tsconfig ./tsconfig.json) — 0 errors"
        status: pass
      - kind: other
        ref: "grep of +page.server.ts confirms no 'incomplete' reference, tab/missing/is_justice present, PersonListItem has argument_count/tenure_coverage/has_tenure_gap and no role_id/role_name"
        status: pass
    human_judgment: false
  - id: D2
    description: "People list is titled 'People' with Bench (default)/Advocate tabs, per-tab columns (tenure coverage + gap indicator on Bench, argument count on Advocate), click-to-filter missing-field pills with active state + Clear filter, Bench-only tenure-gaps toggle, and a Create person button to /admin/people/new"
    requirement: "PDIR-01, PDIR-03, PDIR-04, PDIR-05, PDIR-06, PDIR-07"
    verification:
      - kind: unit
        ref: "npm run check && npm run build — both succeed, 0 errors"
        status: pass
      - kind: other
        ref: "grep of +page.svelte confirms: no 'Show incomplete only' toggle remains; pills are <button> with aria-pressed and aria-label=\"Filter by ...\"; tenure-gaps toggle wrapped in a data.tab === 'bench' conditional; <h1> reads exactly 'People'; Create person link targets /admin/people/new"
        status: pass
      - kind: manual_procedural
        ref: "Manual verification against a running dev server + seeded DB (visiting /admin/people, /admin/people?tab=advocate, clicking a pill, clicking Clear filter) was not performed in this session — no dev server/DB was started"
        status: unknown
    human_judgment: true
    rationale: "Static checks (type-check, build, grep of markup/ARIA attributes) confirm the code is structurally correct and matches the UI-SPEC's copy/attribute requirements, but visual layout, tab-switch behavior, and pill click-through against live data have not been observed running. A human should do a quick pass per the plan's own <verification> section before this is considered fully proven."

# Metrics
duration: 15min
completed: 2026-07-09
status: complete
---

# Phase 27 Plan 4: People List Tabs and Click-to-Filter Summary

**`/admin/people/` is now a tabbed "People" directory (Bench default, Advocate via `?tab=`) with click-to-filter missing-field pills, a Bench-only tenure-gaps toggle, and a "Create person" entry point — all driven by Plan 27-02/27-03's `is_justice`/`missing`/`tenure_gaps` query-param contract**

## Performance

- **Duration:** 15 min
- **Started:** 2026-07-08T23:57:00Z (session context load)
- **Completed:** 2026-07-09T00:02:27Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `+page.server.ts`'s `load` now reads `tab` from the URL (default `'bench'`, D-03), maps it to `is_justice` for the FastAPI call, and forwards a single `missing` field-name filter in place of the deleted `incomplete` toggle (D-04)
- `PersonListItem` extended with `argument_count`/`tenure_coverage`/`has_tenure_gap`, with `role_id`/`role_name` removed (D-10) — matching Plan 27-02/27-03's service/router return shape exactly
- `+page.svelte` rebuilt: page title renamed to "People" (PDIR-01), a Bench/Advocate segmented toggle (Bench default) replaces the removed "Show incomplete only" toggle, and a "Create person" button navigates to `/admin/people/new` (PDIR-07)
- Missing-field pills converted from `<span>` to `<button>` with click-to-filter behavior (single-select, re-click clears), `aria-pressed`/`aria-label` attributes, active-state solid fill, and a hover box-shadow via a new scoped `<style>` block (D-04)
- A persistent "Filtering by: {label} · Clear filter" line renders above the table whenever a missing-field filter or the tenure-gaps toggle is active
- Bench tab renders Name (+ Justice badge)/Tenure coverage/Tenure gap indicator/Missing fields/Actions; Advocate tab renders Name/Argument count (right-aligned)/Missing fields/Actions (PDIR-03/PDIR-04)
- Four distinct empty-state branches implemented per the Copywriting Contract (Bench-no-people, Advocate-no-people, missing-filter-empty, tenure-gaps-filter-empty)
- "Justices with tenure gaps" toggle retained verbatim but now gated to render only on the Bench tab (PDIR-06)

## Task Commits

Each task was committed atomically:

1. **Task 1: Rework the list load function for tab and missing-field params** - `124fd49f` (feat)
2. **Task 2: Rebuild the list component with tabs, click-to-filter pills, and per-tab tables** - `fd0a0cec` (feat)

## Files Created/Modified
- `app/src/routes/admin/people/+page.server.ts` - `load` reads `tab` (default bench) → forwards `is_justice`; adds `missing` filter, drops `incomplete`; `PersonListItem` type updated
- `app/src/routes/admin/people/+page.svelte` - Full restructure: title rename, Bench/Advocate tabs, Create-person button, click-to-filter pills (button + active state + Clear filter), Bench-only tenure-gaps toggle, per-tab columns, four empty states, new scoped `<style>` block for pill hover state

## Decisions Made
- Tab switch clears missing/tenure_gaps filters (both are tab-scoped concepts) — see key-decisions in frontmatter for full rationale.
- Tenure-gaps "Filtering by" label reads "Justices with tenure gaps" (matches the toggle's own label) since the UI-SPEC only explicitly specifies the pill-filter label wording for this line.
- Used `aria-pressed` (not `role="tab"`/`role="tablist"`) on the Bench/Advocate toggle, consistent with the pill-button ARIA idiom already established in this file.
- Added a minimal scoped `<style>` block for the `.pill`/`.pill:hover`/`.pill:focus-visible`/`.pill-active` states since inline `style="..."` attributes cannot express `:hover`/`:focus-visible` — first `<style>` block in this specific route file, following the precedent already used elsewhere in the admin section (`[id]/+page.svelte`, `MobileNavBar.svelte`, `SpeakerPopover.svelte`).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Plan 27-05 (person editor) and Plan 27-06 (create page) are unaffected by this plan's scope — this plan only touched the list page (`+page.server.ts`/`+page.svelte`), matching its `files_modified` declaration exactly.
- The list page's "Edit person" links and new "Create person" button both navigate to routes (`/admin/people/{id}`, `/admin/people/new`) that Plans 27-05/27-06 are responsible for building out; no blocking dependency in the other direction.
- Manual/visual verification against a running dev server + seeded database (per this plan's own `<verification>` section: default Bench tab, `?tab=advocate` argument-count column, pill click/clear round-trip) was not performed in this session — flagged as `human_judgment: true` in the coverage block above for the verifier to route to a human UAT pass.
- No blockers for downstream plans.

---
*Phase: 27-people-admin*
*Completed: 2026-07-09*

## Self-Check: PASSED

- FOUND: app/src/routes/admin/people/+page.server.ts
- FOUND: app/src/routes/admin/people/+page.svelte
- FOUND: .planning/phases/27-people-admin/27-04-SUMMARY.md
- FOUND commit: 124fd49f (Task 1)
- FOUND commit: fd0a0cec (Task 2)
