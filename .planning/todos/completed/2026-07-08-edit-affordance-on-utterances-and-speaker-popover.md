completed: 2026-07-13
---
created: 2026-07-08T21:36:08.025Z
title: Edit affordance on utterances and speaker popover
area: ui
files:

  - app/src/routes/cases/[slug]/arguments/[id]/+page.svelte
  - app/src/lib/components (speaker popover component)

---

## Problem

Operators currently have no way to correct an individual utterance (text or speaker attribution) directly from the public-facing argument view. Corrections today only flow through the admin pipeline resolve step, which only applies at ingest time — there's no path to fix a mistake discovered later while reading a published argument.

Surfaced during Phase 27 (People Admin) discussion — unrelated to that phase's scope, captured for a future phase.

## Solution

TBD. Rough shape from the idea as stated:

- When an authenticated operator is logged in (existing HMAC admin session), every utterance on the public argument page should show an "Edit" affordance.
- The speaker popover card (shown when clicking a speaker avatar) should also gain an "Edit" link, to jump into editing that speaker/utterance.
- Needs a new utterance-level edit surface/endpoint — no such capability exists today (existing edit surfaces are argument-level and person-level only, not utterance-level).
- Auth-gating on a public-facing page is a new pattern — today's admin auth only guards `/admin/*` routes; this would require conditionally rendering admin-only UI on a public route based on session state.
