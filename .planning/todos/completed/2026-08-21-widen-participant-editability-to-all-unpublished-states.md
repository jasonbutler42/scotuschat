---
created: 2026-08-21T00:00:00.000Z
title: Participants should be editable in every state except published, not only in candidate
area: api
severity: enhancement
scheduled: Phase 49 (Review Model) — v1.8
files:
  - api/services/admin_people.py (line 968 — the editability predicate)
  - api/services/admin_jobs.py (lines 285, 591, 719, 825 — MIXED; see classification below)
  - app/src/routes/admin/pipeline/[job_id]/+page.server.ts (line 294 — readonlyMode)
---

## Request

Operator request, made at the Phase 48-09 sign-off walkthrough (2026-08-21),
after confirming the Resolve card is editable on a `candidate` argument:

> "The Resolve card doesn't have the same functionality once it's out of
> Candidate status. I should still be able to edit the people in an argument in
> any state EXCEPT when it's published."

**Current rule:** editable only while `status == CANDIDATE`.
**Requested rule:** editable in `candidate`, `draft`, and `unpublished`;
read-only only when `published`.

## This is a design change, not a bug fix

The CANDIDATE-only rule is deliberate and predates Phase 48.
`api/services/admin_dev.py`'s fixture comments cite "resolve-card editability
keys on `Argument.status` staying CANDIDATE" as an invariant the fixture set is
built to preserve. Phase 48 only retired the old `PIPELINE` vocabulary in favour
of `CANDIDATE` at these sites (plan 48-04); it did not choose the rule.

## Do not mechanically widen every `!= CANDIDATE` check

The `CANDIDATE` comparisons serve two different purposes and only one of them is
about editability. Classify each site before touching it:

| Site | Kind | Action |
|---|---|---|
| `admin_people.py:968` | editability (`editable = status == CANDIDATE`) | widen to `status != PUBLISHED` |
| `admin_jobs.py:285` | editability-adjacent | inspect, likely widen |
| `admin_jobs.py:591` | **`approve_job` double-approve guard** | **MUST stay CANDIDATE-only** |
| `admin_jobs.py:719` | unclassified | inspect individually |
| `admin_jobs.py:825` | unclassified | inspect individually |
| `+page.server.ts:294` | frontend `readonlyMode` | widen to `status === 'published'` |

A find-and-replace across `!= CANDIDATE` would break approve semantics — an
argument would become approvable more than once.

## Trust-tier consequences — the part most likely to be missed

Editing participants changes `derive_tier`'s inputs, so **every newly-reachable
edit path must call `recompute_argument_tier`**. Plan 48-04 wired recompute into
the four `admin_jobs` writers, but widening editability makes write paths
reachable in states where they previously could not run at all. That coverage
needs re-verifying rather than assuming.

Two behavioural interactions to decide deliberately:

1. Editing an `unpublished` argument can drop its tier to `uncertain`, which then
   blocks re-publishing until the operator supplies a fresh override reason.
   Correct per D-16 (overrides are not sticky), but a real workflow consequence.
2. A `draft` argument's tier becoming `uncertain` mid-edit means the publish
   button starts showing the block panel. Expected, but worth confirming it
   reads sensibly rather than looking like an error.

## Why Phase 49

Phase 49 is "Review Model — four-state `review_state` on operator-editable rows,
discrepancy recording on re-import, and a filterable operator review queue."
Which rows are operator-editable, and in which states, is that phase's subject
matter. `review_state` is also already one of `derive_tier`'s three inputs, so
the two changes interact and are better designed together than sequentially.

## Related

- [[2026-08-20-argument-status-card-labels-resolved-at-as-created]] — same detail page

## Resolution (2026-08-23, Phase 49 plan 49-06)

Closed. Backend half landed in plan 49-04 (`admin_people.py`, `admin_jobs.py`
delegation through the authority gate; `update_resolve_row_for_job`'s status
guard and `list_resolve_rows_for_job`'s `editable` flag both widened to
`status != PUBLISHED`). The frontend half — `+page.server.ts:294`'s shared
`readonlyMode` — was deliberately left open by both 49-04 and 49-05 because it
gated two different concerns behind one flag (this Resolve-card widening, and
the unrelated `ArgumentDetailsCard` metadata-edit form). Plan 49-06 split it
into `resolveCardReadonly` (`status === 'published'`, matching this todo's own
`widen to status === 'published'` line) and `metadataReadonly` (unchanged
`status !== 'candidate'`, since `update_argument_metadata` has no status guard
of its own and nothing in this todo or Phase 49's scope asked that concern to
change). No trust-tier recompute gap was found: every Resolve-card write path
this widening makes newly reachable already recomputes via 49-04's own gate
(`apply_participant_value_change` -> `recompute_argument_tier`, exhaustively
tested in `api/tests/test_authority_matrix.py`).
