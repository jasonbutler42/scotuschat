---
created: 2026-08-20T00:00:00.000Z
title: reset_to_fixture writes stale created_at values because it reuses one transaction
area: api
severity: minor
files:
  - api/services/admin_dev.py (reset_to_fixture — shared session across the fixture loop and state realization)
---

## Problem

Found 2026-08-20 by plan 48-09's zero-drift proof. `reset_to_fixture` reuses a
single long-lived FastAPI session/transaction across its fixture-verification
loop and its state-realization step. PostgreSQL's `now()` returns
**transaction-start** time, so `server_default=func.now()` columns written late
in that transaction carry a timestamp from when the transaction opened, not when
the row was inserted.

Observed on the Draft fixture (argument 1785, oyez 13015):

```
log_id=105  candidate  created_at=2026-08-20 17:05:09.085533
log_id=108  draft      created_at=2026-08-20 17:04:20.872746   <- 49s EARLIER
```

The `draft` row was inserted after the `candidate` row (ids prove it) but
carries an earlier timestamp. `arguments.resolved_at` on the same fixture is
skewed the same way.

## What was already fixed, and what is still open

**Fixed in plan 48-10/48-09** — the *display* consequence. The status-history
query in `api/services/admin_arguments.py` ordered by `created_at` first with
`id` only as a tiebreaker, so the skew rendered the Status History **backwards**
on screen (draft above candidate). That query now orders by `id`, which is
monotonic by construction.

**Still open — this todo** — the stored values themselves are wrong. Anything
that reasons about *when* a transition happened, rather than merely its order,
still reads a stale timestamp. Reset-created fixture data is the only known
source today.

## Why it surfaced now

Latent since the reset tool was built. Before plan 48-05, a Draft argument had
exactly one `argument_status_log` row, so a skewed timestamp had nothing to sort
against. 48-05 gave every argument a birth transition, producing two rows whose
timestamp order disagrees with their insertion order — the same shape as the
other two Phase 48 near-misses, where the phase made a pre-existing defect
reachable rather than introducing it.

## Suggested direction

- Commit (or at least flush with a fresh transaction) between the reseed loop
  and the state-realization step, so `now()` advances. Cheapest correct fix.
- Or set the timestamps explicitly in application code rather than relying on
  `server_default=func.now()` for rows written inside a batch transaction.
- Either way, add an assertion to the reset tool's own tests that
  `argument_status_log.created_at` is monotonic with `id` for every seeded
  argument — that is the invariant that silently broke.

## Related

- [[2026-08-20-reset-has-no-timeout-or-progress]] — same function, different defect
- [[2026-08-20-reset-error-copy-overclaims-db-corruption]] — same function again
