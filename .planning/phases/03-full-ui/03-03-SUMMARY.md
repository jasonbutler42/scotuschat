---
phase: 03-full-ui
plan: 03
subsystem: frontend
tags: [sveltekit, svelte5, chatbubble, avatar, alignment, initials]

# Dependency graph
requires:
  - phase: 03-full-ui
    plan: 01
    provides: GET /cases FastAPI endpoint (foundation for case browsing)
provides:
  - ChatBubble.svelte with 32px avatar circle (initials-only, bench slate, advocate blue)
  - D-05 alignment flip: bench LEFT (flex-start), advocate RIGHT (flex-end)
  - avatarBg and initials computed values derived from $props() in Svelte 5 Runes
affects: [03-04, 03-full-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Avatar initials IIFE: first letter of first + last word of displayName, toUpperCase(); single-word fallback to first 2 chars"
    - "Svelte 5 Runes: plain const IIFE for synchronous derived value from $props() — not $derived (no reactivity needed, value fixed at instantiation)"
    - "No img elements for avatars — initials-only; photo_url deferred to v2 per 02-CONTEXT.md D-11"

key-files:
  created: []
  modified:
    - app/src/lib/components/ChatBubble.svelte

key-decisions:
  - "D-05 alignment flip: bench LEFT (flex-start) / advocate RIGHT (flex-end) — reverses Phase 1 to match header roster spatial layout"
  - "avatarBg matches existing labelColor logic: bench #94a3b8, advocate #93c5fd — consistent per D-08"
  - "Avatar initials use 12px/600 as documented UI-SPEC exception (not a declared type role) — not 13px which is the Label role"
  - "Plain const IIFE (not $derived) for initials — value is fixed at component instantiation from $props(), no reactive recomputation needed"

requirements-completed: [UI-05]

# Metrics
duration: 15min
completed: 2026-06-12
---

# Phase 3 Plan 03: ChatBubble Avatar Circle and Alignment Flip Summary

**32px avatar circle with initials (bench slate #94a3b8, advocate blue #93c5fd, dark text #0f1117) added to ChatBubble.svelte; bench/advocate alignment flipped per D-05 (bench LEFT, advocate RIGHT)**

## Performance

- **Duration:** 15 min
- **Started:** 2026-06-12T00:00:00Z
- **Completed:** 2026-06-12T00:15:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Applied four targeted edits to `app/src/lib/components/ChatBubble.svelte`:
  1. D-05 alignment flip: outer flex `justify-content` changed from `isBench ? 'flex-end' : 'flex-start'` to `isBench ? 'flex-start' : 'flex-end'` — bench now aligns LEFT, advocates RIGHT
  2. Script additions: `avatarBg` (isBench ? '#94a3b8' : '#93c5fd') and `initials` IIFE constant added after `displayRole`
  3. Avatar circle div inserted as first child in the bubble header row: 32px circle, border-radius 50%, background-color from `avatarBg`, font-size 12px, font-weight 600, color #0f1117 (dark), flex-shrink 0
  4. Header row gap increased from `gap: 4px` to `gap: 8px` to accommodate the avatar element
- No `export let`, no `$:` reactive blocks, no `onMount` — pure Svelte 5 Runes throughout
- No `<img>` elements — initials-only as per Phase 3 scope; `photo_url` deferred to v2

## Task Commits

Note: Git was not initialized in the project directory (same situation as Plans 03-01 and 03-02). File edits were completed successfully.

1. **Task 1: Add 32px avatar circle and flip bench/advocate alignment in ChatBubble.svelte** — app/src/lib/components/ChatBubble.svelte modified

## Files Created/Modified

- `app/src/lib/components/ChatBubble.svelte` — Added `avatarBg` and `initials` constants; avatar circle div (32px, border-radius 50%, dark text) inserted before sequence number span in header row; gap increased to 8px; outer flex justify-content flipped for D-05

## Decisions Made

- Plain `const` IIFE used for `initials` (not `$derived`) — value is computed synchronously at component instantiation from `$props()`, no reactive recomputation needed
- Avatar font-size 12px/600 as documented UI-SPEC exception — not subject to 4-size type scale restriction
- Comment updated to "D-05: BENCH: left-aligned; ADVOCATE or UNKNOWN: right-aligned" for clarity

## Deviations from Plan

None - plan executed exactly as written. All four edits match the PATTERNS.md and UI-SPEC contracts exactly.

## Known Stubs

None. Avatar circle is fully wired: `avatarBg` derived from `utterance.side`, `initials` computed from `utterance.speaker_name ?? utterance.raw_speaker_label`. No placeholder or synthetic data. The `photo_url` path is intentionally deferred (v2) and not a stub in this component.

## Threat Flags

No new threat surface beyond the plan's documented threat_model:
- T-03-03-01 (initials from speaker_name): initials rendered as plain text content in a div (not innerHTML, not eval); first/last character extraction from displayName produces at most 2 characters; no XSS surface — accept disposition honored

## Self-Check

**Files modified:**

- `app/src/lib/components/ChatBubble.svelte`: EXISTS and contains:
  - `justify-content: {isBench ? 'flex-start' : 'flex-end'}` (D-05 flip, bench LEFT): YES
  - Does NOT contain `justify-content: {isBench ? 'flex-end' : 'flex-start'}` (old alignment): CORRECT
  - `avatarBg` constant defined as `isBench ? '#94a3b8' : '#93c5fd'`: YES
  - `initials` constant with `split(/\s+/)` algorithm: YES
  - `border-radius: 50%` (avatar circle): YES
  - `font-size: 12px` on avatar circle: YES
  - `color: #0f1117` on avatar circle: YES
  - `width: 32px` and `height: 32px` on avatar circle: YES
  - `gap: 8px` on header row: YES
  - No `export let`: CORRECT
  - No `$:`: CORRECT
  - `avatarBg` appears >= 2 times (defined + used in template): YES (2 occurrences)

**Acceptance criteria verified:**

- ChatBubble.svelte contains `justify-content: {isBench ? 'flex-start' : 'flex-end'}`: YES
- ChatBubble.svelte does NOT contain `justify-content: {isBench ? 'flex-end' : 'flex-start'}`: YES
- ChatBubble.svelte contains `avatarBg` defined as `isBench ? '#94a3b8' : '#93c5fd'`: YES
- ChatBubble.svelte contains `initials` with `split(/\s+/)` algorithm: YES
- ChatBubble.svelte contains `border-radius: 50%`: YES
- ChatBubble.svelte contains `font-size: 12px` on avatar circle: YES
- ChatBubble.svelte contains `color: #0f1117` on avatar circle: YES
- ChatBubble.svelte contains `width: 32px` and `height: 32px`: YES
- ChatBubble.svelte contains `gap: 8px` on header row: YES
- ChatBubble.svelte does NOT contain `export let`: YES
- ChatBubble.svelte does NOT contain `$:`: YES
- `avatarBg` count >= 2: YES (2 matches)

## Self-Check: PASSED

---
*Phase: 03-full-ui*
*Completed: 2026-06-12*
