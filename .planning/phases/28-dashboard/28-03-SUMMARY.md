---
phase: 28-dashboard
plan: 03
subsystem: app
tags: [sveltekit, svelte5-runes, dashboard, admin-ui]

# Dependency graph
requires:
  - phase: 28-dashboard
    provides: "Plan 02's seven GET routes on api/routers/admin.py (/arguments/stats, /arguments/recent-drafts, /people/stats, /people/incomplete, /people/tenure-gaps, /jobs/stats, /utterances/count)"
provides:
  - "app/src/lib/components/StatCard.svelte — first shared admin card component in the codebase"
  - "Rewritten /admin/ dashboard: Needs Attention section, four stat cards, Web Traffic placeholder"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "First shared Svelte component (StatCard.svelte) composed via a children snippet, replacing per-page inline card markup for this page"
    - "Sequential degrade-gracefully load() with 7 independent try/catch blocks, null-sentinel stat values vs. [] sub-list defaults, matching the pipeline job detail page's established pattern"

key-files:
  created:
    - app/src/lib/components/StatCard.svelte
  modified:
    - app/src/routes/admin/+page.server.ts
    - app/src/routes/admin/+page.svelte

key-decisions:
  - "Missing-fields per-row copy on the People Needs Attention sub-list uses a generated '{n} missing field(s)' label (singular/plural) since the UI-SPEC didn't specify exact per-row wording beyond 'missing-field count (muted Label)'"
  - "last_activity_at renders 'N/A' both when the fetch failed AND when the value is genuinely null (no jobs exist yet) — the UI-SPEC's Load-failure table has no separate 'genuinely empty' state for this field, and N/A is the established project-wide 'value not available' convention"
  - "Stat-card grid uses a 4-column CSS grid with a 32px (xl) gap, per UI-SPEC Layout & Component Notes"

requirements-completed: [DASH-01, DASH-02, DASH-03, DASH-04, DASH-05]

coverage:
  - id: T1
    description: "StatCard.svelte compiles under svelte-check, uses \$props() with no export let, and has a fixed (non-conditional) container style"
    requirement: "DASH-05"
    verification:
      - kind: unit
        ref: "npx svelte-check --tsconfig ./tsconfig.json (0 errors)"
        status: pass
    human_judgment: false
  - id: T2
    description: "load() fetches all seven Plan 02 endpoints sequentially (no Promise.all), preserves the logout action, and never throws error()/redirect() on fetch failure"
    requirement: "DASH-01, DASH-03"
    verification:
      - kind: unit
        ref: "npx svelte-check + grep assertions (Promise.all count=0, logout present, 7 distinct FASTAPI_BASE_URL calls, no error( import)"
        status: pass
    human_judgment: false
  - id: T3
    description: "Dashboard renders Needs Attention first, four neutral stat cards with correct CTAs, and a visually-distinct Web Traffic placeholder; svelte-check and build both pass"
    requirement: "DASH-01, DASH-02, DASH-03, DASH-04, DASH-05"
    verification:
      - kind: unit
        ref: "npx svelte-check + npm run build (both pass, 0 errors) + source-assertion greps for hrefs/prohibitions"
        status: pass
    human_judgment: true
---

# Phase 28 Plan 03: Dashboard Frontend Summary

**Rewrote `/admin/` from a placeholder into an at-a-glance operator dashboard: a new shared `StatCard.svelte` component, a sequential degrade-gracefully `load()` fetching all seven Plan 02 endpoints, and a `+page.svelte` rendering Needs Attention first, four neutral stat cards, then a visually-distinct Web Traffic placeholder — all from DESIGN-SYSTEM.md tokens with no mockup pass.**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-07-11
- **Tasks:** 3
- **Files modified:** 3 (1 new, 2 rewritten)

## Accomplishments

- `app/src/lib/components/StatCard.svelte` — first shared card component in the codebase; Svelte 5 runes only (`$props`), fixed neutral container style (`#1e293b`/`#334155`) never conditional on counts (D-10), composes each card's differently-shaped breakdown via a `children` snippet
- `app/src/routes/admin/+page.server.ts` — new `load()` performs seven sequential fetches (arguments/stats, people/stats, jobs/stats, utterances/count, arguments/recent-drafts, people/incomplete, people/tenure-gaps), each independently try/catch-wrapped with a null-count sentinel (stats) or `[]` (sub-lists) on failure; never hard-errors; existing `logout` action preserved verbatim
- `app/src/routes/admin/+page.svelte` — full rewrite: Needs Attention section (People/Justices/Drafts sub-lists, capped at 5, "View all" links, whole-section "All caught up" empty state) renders first (D-09), followed by the 4-card stat grid (Arguments' three status deep-links, People's unfiltered CTA per D-05 amendment, Utterances with no CTA, Pipeline's 30-day count + last-activity + unfiltered CTA per D-07), then the Web Traffic placeholder in its own row (dashed border, reduced opacity, D-12)
- Failed-value rendering: `formatCount()`/`formatDate()` helpers render `"N/A"` (never a bare `0` or em-dash) for any null stat value

## Task Commits

Each task was committed atomically:

1. **Task 1: Create shared StatCard.svelte component** - `d69c9d42` (feat)
2. **Task 2: Add load() to +page.server.ts fetching the seven endpoints (preserve logout)** - `39c85cb9` (feat)
3. **Task 3: Rewrite +page.svelte — Needs Attention section, stat grid, placeholder** - `76c679f8` (feat)

**Plan metadata:** commit pending (see below)

## Files Created/Modified

- `app/src/lib/components/StatCard.svelte` - new: shared stat-card container, `title` + `children` snippet props
- `app/src/routes/admin/+page.server.ts` - rewritten: added `load()` with 7 sequential degrade-gracefully fetches; `logout` action unchanged
- `app/src/routes/admin/+page.svelte` - rewritten: Needs Attention section, 4-card stat grid, Web Traffic placeholder, replacing the prior single-line placeholder body

## Decisions Made

- Missing-fields per-row copy on the People Needs Attention sub-list generates `"{n} missing field(s)"` (singular/plural) — the UI-SPEC specified the row shape ("missing-field count, muted Label") but not an exact literal string for this specific count
- `last_activity_at` renders `"N/A"` both on fetch failure and on a genuinely-null value (no pipeline runs yet exist) — no separate copy exists for that distinction in the UI-SPEC, and `"N/A"` is the established project-wide "value not available" convention
- Stat-card grid uses a 4-column CSS grid with a 32px (`xl`) gap between cards, per UI-SPEC Layout & Component Notes

## Deviations from Plan

None - plan executed exactly as written. All three tasks' automated verify commands (`svelte-check`, `npm run build`, and the source-assertion greps for hrefs/prohibitions/Promise.all/logout) passed on the first attempt with no auto-fixes required.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 28 (Dashboard) is now fully implemented across all three plans (28-01 backend data layer, 28-02 router endpoints, 28-03 frontend). All 5 requirements (DASH-01 through DASH-05) have shipped code behind them.
- No blockers. Manual/visual UAT of the rendered dashboard (e.g. confirming the calm, non-alarming visual hierarchy reads correctly against live data) is expected to happen via `/gsd-verify-work 28`, not this executor.

---
*Phase: 28-dashboard*
*Completed: 2026-07-11*
