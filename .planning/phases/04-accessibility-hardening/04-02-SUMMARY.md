---
phase: 04-accessibility-hardening
plan: "02"
subsystem: frontend
tags: [accessibility, wcag, landmarks, mobile-nav, aria, color-contrast]
dependency_graph:
  requires: [04-01]
  provides: [mobile-nav-bar, html-landmarks, roster-color-fix]
  affects:
    - app/src/lib/components/MobileNavBar.svelte
    - app/src/routes/+layout.svelte
    - app/src/routes/cases/+page.svelte
    - app/src/routes/cases/[slug]/arguments/[id]/+page.svelte
tech_stack:
  added: []
  patterns: [fixed-bottom-pill-nav, intersection-observer-scroll-spy, html5-landmarks, wcag-landmark-roles]
key_files:
  created:
    - app/src/lib/components/MobileNavBar.svelte
  modified:
    - app/src/routes/+layout.svelte
    - app/src/routes/cases/+page.svelte
    - app/src/routes/cases/[slug]/arguments/[id]/+page.svelte
decisions:
  - D-08: +layout.svelte nav wrapped in <header>; aria-label="Site navigation" on nav — correct WCAG landmark
  - D-08: cases/+page.svelte outer div → <main>; top-bar div → <header> — semantic page structure
  - D-08: argument page outer div → <main>; heading bar div → <header> — semantic page structure
  - D-03: Roster column headers color #475569 → #94a3b8 — achieves 4.5:1 contrast; #475569 now absent from entire app/src tree
  - D-11/D-12/D-13: MobileNavBar.svelte created as Svelte 5 Runes component — fixed-bottom pill nav, IntersectionObserver scroll-spy, hidden on desktop / shown at max-width 768px
  - D-13: Chat column bottom padding increased to 60px — prevents last utterance hiding behind fixed MobileNavBar on narrow viewports
metrics:
  duration_seconds: 164
  completed_date: "2026-06-15"
  tasks_completed: 3
  tasks_total: 3
  files_created: 1
  files_modified: 3
---

# Phase 4 Plan 02: MobileNavBar, HTML Landmarks, Roster Color Fix Summary

**One-liner:** New MobileNavBar.svelte component (fixed-bottom pill nav with scroll-spy) plus surgical landmark HTML and #475569 elimination completing WCAG 2.1 AA compliance across all four pages.

## Tasks Completed

| Task | Name | Commit | Key Changes |
|------|------|--------|-------------|
| 1 | Create MobileNavBar.svelte | 44623ee | New component: position:fixed bottom-0, IntersectionObserver scroll-spy, pill buttons, 768px media query, Svelte 5 Runes |
| 2 | +layout.svelte and cases/+page.svelte — HTML landmarks | 1a9703f | layout: nav wrapped in `<header>`, `aria-label="Site navigation"`; cases page: outer `<main>`, top-bar `<header>` |
| 3 | argument page — landmarks, roster color fix, MobileNavBar integration | d900f78 | `<main>`/`<header>` landmarks; Bench/Advocates headers #475569 → #94a3b8; 60px chat padding; MobileNavBar wired |

## Verification Results

1. `#475569` completely absent from `app/src/` tree — `grep -r "#475569" app/src/` returns no matches.
2. MobileNavBar.svelte exists with `position: fixed`, `bottom: 0`, `min-height: 44px`, and `@media (max-width: 768px)` show rule.
3. `+layout.svelte` has `<header>` wrapping `<nav aria-label="Site navigation">`.
4. `cases/+page.svelte` has `<main>` outer and `<header>` top-bar.
5. Argument page has `<main>` outer, `<header>` heading bar, and `<MobileNavBar sections={sectionAnchors} />` before `</main>`.
6. Chat column padding is `48px 24px 60px 24px`.
7. `npm run check` — 0 errors, 5 pre-existing warnings (ChatBubble state reference, tsconfig node types).
8. No `PUBLIC_` env vars introduced.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — MobileNavBar receives real `sectionAnchors` data derived from utterances. No placeholder values introduced.

## Threat Flags

None — changes are HTML element upgrades (div → semantic landmark), color value changes, and a new client-side component that reads server-side-fetched utterance data. No new network endpoints, auth paths, or trust boundaries introduced. T-04-02-01 and T-04-02-02 both accepted per threat register.

## Self-Check: PASSED

- [x] app/src/lib/components/MobileNavBar.svelte — exists, contains `position: fixed`, `@media (max-width: 768px)`, scroll-spy IntersectionObserver
- [x] app/src/routes/+layout.svelte — exists, contains `<header>`, `aria-label="Site navigation"`
- [x] app/src/routes/cases/+page.svelte — exists, contains `<main`, `<header`
- [x] app/src/routes/cases/[slug]/arguments/[id]/+page.svelte — exists, contains `<main`, `<header`, `<MobileNavBar`, `60px`, no `#475569`
- [x] grep -r "#475569" app/src/ — no matches
- [x] Commits 44623ee, 1a9703f, d900f78 verified in git log
