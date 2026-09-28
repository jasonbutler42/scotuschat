---
created: 2026-09-25T00:00:00.000Z
title: A third, independent initials splitter survives in admin ResolveCard.svelte
area: ui
priority: low
files:
  - app/src/lib/admin/ResolveCard.svelte
resolves_phase: 52
---

> **Scheduled 2026-09-25.** Operator decision: this is fixed in plan `52-06`
> (wave 3 of phase 52), not deferred to the backlog. 52-02's D-12 must_have was
> amended to scope it to public surfaces, with codebase-wide singularity left as
> 52-06's truth to satisfy. `resolves_phase: 52` closes this todo automatically
> when the phase completes.

## Problem

Phase 52-02 (D-12) retired the two public-surface client-side initials
splitters — `SpeakerPopover.svelte`'s `$derived.by` block and
`arguments/[slug]/+page.svelte`'s `getInitials` — replacing both with a
single server-computed `derive_initials` (`api/domain/person_names.py`),
shipped on `SpeakerPopoverEntry.initials` and
`UtteranceResponse.speaker_initials`.

A third, byte-identical copy of the same splitting logic exists in
`app/src/lib/admin/ResolveCard.svelte:763` (`getInitials`, one call site at
line 1236), used to render an avatar badge for a candidate/unresolved
speaker during the admin resolve workflow. 52-CONTEXT.md's own "Claude's
Discretion" note ("Converging the two initials helpers") and the 52-02 plan's
`files_modified` list only named the two public-surface copies — this admin
copy was not discovered during Phase 52 research/context-gathering, so it
was left untouched rather than silently pulled into scope.

## Why it matters

D-12's stated goal was "one implementation, one place to test" so a third
splitter can't reappear by accident. This admin copy means that goal is not
yet fully met — a third independent implementation of the same string-split
logic still exists, just outside the public surface D-12 targeted. It is not
a live bug (`ResolveCard.svelte`'s rendering is unaffected and correct for
its current inputs), but it's the same maintenance hazard D-12 was written
to close.

## Constraint on any fix

The admin resolve flow's candidate/unresolved-speaker names may not always
correspond to a persisted `Person` row with structured `first_name`/
`last_name` parts (that's part of what "unresolved" means) — so wiring this
call site to the server-side `derive_initials` result is not a pure
delete-and-replace the way the two public call sites were. It needs its own
look at what data is actually available at that point in the admin resolve
flow before deciding whether to converge it onto `derive_initials`,
introduce a matching admin-side helper that calls into the same domain
function, or leave it as a deliberately separate admin-only concern.

## Suggested approach

Scope question for the operator, not a correctness fix: decide whether this
belongs in a future phase (converge onto `api.domain.person_names
.derive_initials` via a new admin-read field, or an admin-side equivalent)
or is accepted as intentionally out of D-12's scope, since it never touches
a public-facing payload.
