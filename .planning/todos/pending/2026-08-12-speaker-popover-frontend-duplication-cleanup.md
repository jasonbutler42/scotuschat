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
