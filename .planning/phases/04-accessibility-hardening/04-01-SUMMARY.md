---
phase: 04-accessibility-hardening
plan: "01"
subsystem: frontend
tags: [accessibility, wcag, aria, color-contrast, focus-ring]
dependency_graph:
  requires: []
  provides: [global-focus-ring, chat-bubble-aria, stage-direction-role, section-rail-nav-label]
  affects: [app/src/app.css, app/src/lib/components/ChatBubble.svelte, app/src/lib/components/StageDirection.svelte, app/src/lib/components/SectionRail.svelte]
tech_stack:
  added: []
  patterns: [wcag-2.1-aa-contrast, focus-visible-ring, aria-article-labeling, aria-note-role, aria-nav-label]
key_files:
  created: []
  modified:
    - app/src/app.css
    - app/src/lib/components/ChatBubble.svelte
    - app/src/lib/components/StageDirection.svelte
    - app/src/lib/components/SectionRail.svelte
decisions:
  - D-01: Removed --color-text-sequence: #475569 from :root — variable is now dead; all sequence spans deleted from ChatBubble
  - D-02: Role label span color in ChatBubble changed from #475569 to #94a3b8 — achieves 4.5:1 contrast on #1e293b surface
  - D-05/D-06/D-07: Global focus ring added to app.css — 2px solid #93c5fd, 3px offset, 4px border-radius on *:focus-visible
  - D-08: aria-label="Argument sections" added to SectionRail <nav> — correct landmark for assistive technology
  - D-09: role="article" + aria-label="{side}: {displayName}" on ChatBubble outer wrapper — screen readers announce each utterance with speaker context
  - D-10: role="note" on StageDirection outer div — distinguishes stage directions from spoken content in virtual cursor
metrics:
  duration_seconds: 90
  completed_date: "2026-06-15"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 4
---

# Phase 4 Plan 01: Accessibility Fixes (Color Contrast, Focus Ring, ARIA Semantics) Summary

**One-liner:** Surgical four-file WCAG 2.1 AA patch — global focus ring in app.css, sequence span removal and ARIA article semantics in ChatBubble, role=note in StageDirection, nav label in SectionRail.

## Tasks Completed

| Task | Name | Commit | Key Changes |
|------|------|--------|-------------|
| 1 | app.css — remove sequence variable, add global focus ring | a03f38b | Removed `--color-text-sequence`; added `*:focus-visible` rule |
| 2 | ChatBubble.svelte — sequence span, role label color, article role | a4b2414 | Deleted sequence `<span>`; `#475569` → `#94a3b8` on role label; `role="article"` + `aria-label` on outer div |
| 3 | StageDirection + SectionRail — ARIA role and nav label | 612bc3d | `role="note"` on StageDirection outer div; `aria-label="Argument sections"` on SectionRail `<nav>` |

## Verification Results

1. `#475569` eliminated from all 4 modified files — zero occurrences remain in the plan's scope files.
2. `*:focus-visible` block present in app.css with `outline: 2px solid #93c5fd; outline-offset: 3px; border-radius: 4px`.
3. `utterance.sequence` removed from ChatBubble.svelte — sequence numbers no longer rendered.
4. `role="article"` and `aria-label="{isBench ? 'Bench' : 'Advocate'}: {displayName}"` present on ChatBubble outer wrapper.
5. `role="note"` present on StageDirection outer div.
6. `aria-label="Argument sections"` present on SectionRail `<nav>`.

## Deviations from Plan

### Out-of-Scope Discoveries

**1. [Out of scope] #475569 in +page.svelte roster column headers**
- **Found during:** Overall verification (cross-codebase grep)
- **Description:** `+page.svelte` contains `color: #475569` on two roster column header elements ("Bench", "Advocates" labels at font-size 13px/600). These are pre-existing occurrences in a file outside this plan's `files_modified` list.
- **Resolution:** Intentionally deferred — the plan's must_haves explicitly notes "roster column headers passes 4.5:1 contrast (fix applied in Plan 04-02)". This is tracked scope for Plan 04-02 and logged here for the verifier.
- **Logged in:** This summary (not deferred-items.md — the deferral is already documented in the plan itself)

## Known Stubs

None — all modified components render real data from props. No placeholder values introduced.

## Threat Flags

None — changes are CSS attribute additions and ARIA attribute additions only. No new network endpoints, auth paths, or trust boundaries introduced. `aria-label` interpolates `displayName` which is the same speaker name already rendered as visible text (T-04-01 accepted).

## Self-Check: PASSED

- [x] app/src/app.css — exists, contains `*:focus-visible`, no `--color-text-sequence`, no `#475569`
- [x] app/src/lib/components/ChatBubble.svelte — exists, contains `role="article"`, no `#475569`, no `utterance.sequence`
- [x] app/src/lib/components/StageDirection.svelte — exists, contains `role="note"`
- [x] app/src/lib/components/SectionRail.svelte — exists, contains `aria-label="Argument sections"`
- [x] Commits a03f38b, a4b2414, 612bc3d verified in git log
