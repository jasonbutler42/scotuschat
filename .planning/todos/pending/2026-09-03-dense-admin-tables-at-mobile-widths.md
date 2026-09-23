---
created: 2026-09-03
kind: defect
source: operator, Phase 51 plan 51-10 Task 3 walkthrough (stop 07)
resolves_phase: null
priority: low
audit_acknowledged:
  milestone: v1.8
  at: 2026-09-23
---

# Dense admin tables read badly at mobile widths

Operator: *"The dense tables get weird at mobile sizes but I can live with it for now. but
they should be looked at."*

Explicitly accepted for now — filed so the observation is not lost, not to schedule work.

## Context

Phase 51 plan 51-10 D-04 already fixed the specific starvation case: four of the six columns
on `/admin/review`'s arguments table are `white-space: nowrap`, so each claims its full
min-content width and the one flexible column holding long text was left 125px at any
viewport. `min-width: 22ch` on the case-name column and `18ch` on the people tab's full-name
column took the tallest row from 196px to 101px.

That fixed starvation. It did not make a six-column dense table a good phone experience — the
container scrolls horizontally by design (G-49-5a), and the operator is reporting how that
feels rather than a specific broken column.

## Worth considering when picked up

Whether a dense admin table should reflow to a card-per-row below some width, rather than
scroll. That is a different pattern, not a tuning of this one, and it is the operator's call
on which admin surfaces deserve it.
