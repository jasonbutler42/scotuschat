completed: 2026-08-23
---
---
created: 2026-08-11T14:22:12.986Z
title: Create-person popover should inherit row's side and auto-select the new person
area: ui
severity: minor
files:
  - app/src/lib/components/CreatePersonPopover.svelte
  - app/src/lib/components/ResolveCard.svelte (handlePersonCreated, defaultAdvocateSide prop)
---

## Problem

Found live during Phase 44-09 checkpoint testing (2026-08-10), after fixing the
popover's full_name/422 bug (see `d3f8b965`). Two related UX gaps in the
Resolve card's "Create new bench/advocate person" flow, both confirmed by the
operator, neither urgent enough to fix immediately:

1. **Popover's Bench/Advocate default ignores the row's own toggle.**
   `CreatePersonPopover.svelte` always initializes its internal `side` state
   to `'ADVOCATE'` (`let side = $state<'BENCH' | 'ADVOCATE'>('ADVOCATE');`),
   regardless of what the row's own Bench/Advocate segmented toggle
   (`sideToggle` snippet in `ResolveCard.svelte`) currently shows. An operator
   who has already set a row to Bench, then opens "Create new person," has to
   remember to also click "Bench" a second time inside the popover — an easy
   step to miss, and if missed, the new person is created with the wrong
   `is_justice`/side.

2. **Newly created person isn't visibly selected afterward.**
   `handlePersonCreated` (in `ResolveCard.svelte`) correctly sets
   `s.personId = enriched.id`, so the row IS internally resolved to the new
   person — but it never updates `s.comboQuery`, so the Resolved As search
   box's displayed text stays whatever the operator had typed (or blank)
   before opening the create-person popover. The row is actually resolved,
   but visually looks unresolved/untouched, which reads as "did creating this
   person even do anything?"

## Solution

TBD, but the shape is clear from the two gaps above:

1. `CreatePersonPopover` already accepts a `defaultAdvocateSide` prop (used to
   pick which specific advocate role a created advocate gets). It has no
   equivalent input for which of Bench/Advocate should be pre-selected — the
   parent (`personDropdown` snippet in `ResolveCard.svelte`) already computes
   the row's current `side` and passes it down for other purposes, so wiring
   an initial-side prop through should be straightforward. Needs to only set
   the *initial* value (the operator can still change it inside the popover),
   not force it — `resetForm()`'s hardcoded `side = 'ADVOCATE'` reset would
   also need to reset to this same inherited default instead.
2. In `handlePersonCreated`, set `s.comboQuery = enriched.full_name` alongside
   the existing `s.personId = enriched.id`, mirroring what the click/Enter
   handlers in `personDropdown` already do for an existing-person pick
   (`s!.comboQuery = candidate.full_name; handleSelectPerson(...)`).
