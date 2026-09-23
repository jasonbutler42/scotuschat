---
created: 2026-08-12T00:00:00.000Z
title: Reduce duplication in speaker popover frontend files
area: ui
priority: low
resolves_phase: 51
files:
  - app/src/lib/components/SpeakerPopover.svelte
  - app/src/routes/cases/[slug]/arguments/[id]/+page.svelte
---

## Problem

Surfaced by Phase 45's code review (45-REVIEW.md, IN-02/IN-03), out of
scope for that phase (pre-existing, cosmetic quality items, not bugs).

1. `SpeakerPopover.svelte` computes `avatarBg` and `sideColor` with the
   exact same expression (`isBench ? '#94a3b8' : '#93c5fd'`), then uses
   them interchangeably — dead duplication that could drift out of sync.
2. Both `SpeakerPopover.svelte` and `+page.svelte` declare byte-for-byte
   identical `TenureRow` and `SpeakerDetail` TypeScript interfaces
   (including the same comments). A future field addition/rename risks
   being applied to only one copy.

## Suggested fix

- Collapse `avatarBg`/`sideColor` into one constant.
- Extract `TenureRow`/`SpeakerDetail` into a shared module (e.g.
  `$lib/types/speaker.ts`) and import from both call sites.

## Resolution (2026-08-28, Phase 51 plan 51-07)

Closed exactly as suggested. `app/src/lib/types/speaker.ts` (new module,
framework-free, matches the `participantSide.ts` convention) now holds the
single `TenureRow`/`SpeakerDetail` declaration, moved verbatim (field for
field, no shape change) from `SpeakerPopover.svelte` and
`app/src/routes/arguments/[slug]/+page.svelte` (the file this todo names as
`.../cases/.../+page.svelte` moved during plan 51-02's D-10 route rename).
Both call sites now import the type. `SpeakerPopover.svelte`'s duplicated
`avatarBg`/`sideColor` — both computed from the identical
`isBench ? '#94a3b8' : '#93c5fd'` ternary — collapsed into one `sideColor`
computation site referencing `var(--color-side-bench)` /
`var(--color-side-advocate)`, used at every site that previously read either
variable.
