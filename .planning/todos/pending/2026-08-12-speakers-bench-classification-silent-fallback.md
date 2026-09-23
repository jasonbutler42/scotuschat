---
created: 2026-08-12T00:00:00.000Z
title: Bench/advocate classification has a silent wrong-label fallback if ArgumentParticipant.side is missing
area: api
priority: low
files:

  - api/services/speakers.py

audit_acknowledged:
  milestone: v1.8
  at: 2026-09-23
---

## Problem

Surfaced by Phase 45's code review (45-REVIEW.md, WR-03), out of scope for
that phase (pre-existing, not touched by BUG-01/BUG-02).

`get_argument_speakers()` decides whether to run the tenure-based title
lookup solely from `side == SideEnum.BENCH` (`side` comes from
`ArgumentParticipant.side`). If that row is ever missing or NULL for a
resolved Justice (e.g. a resolve-step data gap), `side` is `None`, the
bench branch is skipped, and the code falls straight into
`ADVOCATE_LABEL_MAP.get(side or SideEnum.UNKNOWN)` → `"Counsel"`. A
sitting/former Justice would silently render with an advocate-style role
pill and no tenure history would even be looked up.

Separately, `app/src/routes/.../+page.server.ts` derives its own
independent `is_bench` flag from `tenure.length > 0` for the same payload —
a second, non-reconciled source of truth for the same fact, which can
diverge from `side` without either code path treating the mismatch as an
error.

## Suggested fix

```python
if side == SideEnum.BENCH or (side is None and person.id in date_tenures_by_person):
    role_name = _tenure_role_name(date_tenures_by_person.get(person.id) or [], argued_date)
else:
    role_name = ADVOCATE_LABEL_MAP.get(side or SideEnum.UNKNOWN)
```

Consider also reconciling the two `is_bench` signals (backend `side`,
frontend `tenure.length > 0`) or at least logging when they disagree.
