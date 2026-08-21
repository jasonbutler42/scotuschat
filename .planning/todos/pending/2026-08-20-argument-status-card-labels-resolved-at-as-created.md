---
created: 2026-08-20T00:00:00.000Z
title: Argument Status card labels resolved_at as "Created"; Argument has no created_at column
area: ui
severity: minor
files:
  - app/src/routes/admin/arguments/[id]/+page.svelte (~line 343)
  - api/models/models.py (Argument — no created_at column)
---

## Problem

Noticed 2026-08-20 during the Phase 48-10 step-9 walkthrough. The operator
nulled `arguments.resolved_at` on one argument to test the non-overridable
publish gate, and observed that the Status card's "Created" date vanished.

It vanished because the card never showed a creation date in the first place —
line ~343 renders the **resolve** timestamp under a "Created" label:

```svelte
{#if data.argument.resolved_at}
  Created {formatDate(data.argument.resolved_at)}
```

`resolved_at` is when the resolve pipeline step completed, which is not when
the argument was created. The two can be far apart — an argument sits in
`candidate` from import until an operator approves its job.

## Why it was not simply fixed

**The `Argument` model has no `created_at` column.** Other models have one
(`models.py` lines 444, 502, 532, 577), but `Argument` does not, so there is no
true creation timestamp to display. Fixing the label properly is a decision,
not a rename:

1. **Relabel to "Resolved"** — honest about what the value is, zero schema
   change, and consistent with the pipeline vocabulary the admin UI already
   uses elsewhere. Cheapest correct option.
2. **Add `Argument.created_at`** via a migration (`server_default=func.now()`)
   and show it alongside the resolve date. More informative, but existing rows
   would all backfill to the migration timestamp rather than their real
   creation time, which is its own small lie.
3. **Derive it from the audit trail** — the earliest `argument_status_log` row
   is now a genuine birth record for every argument, since plan 48-05 made all
   four pipeline writers log a birth transition on arrival. This is arguably the
   most accurate source available, and needs no schema change. Only valid for
   arguments imported after 48-05 landed.

Option 3 is the most interesting given what Phase 48 just built, and it pairs
naturally with the Status history list already rendered on the same card.

## Related

- The same card's "Published" label has a comparable honesty problem, addressed
  during plan 48-10: it showed a publish date on an `unpublished` argument
  because D-02 deliberately retains `published_at`.
