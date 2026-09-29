---
created: 2026-09-29T00:00:00.000Z
title: Show Reset-to-Fixture progress as a progress bar in the admin dev-tools card
area: ui
priority: low
files:

  - app/src/routes/admin/+page.svelte (Reset to Fixture running state, resetProgressText)
  - app/src/routes/admin/dev-fixture-state/+server.ts (the poll source)
  - api/schemas/admin_dev.py (ResetProgress)
---

## Enhancement

Requested by the operator on 2026-09-29, during Phase 53 UAT. Future enhancement, not
a defect. Do not change the current behavior until this is planned.

While a reset runs, the admin page's dev-tools card shows only a one-line text status,
added in Phase 52-05: "Seeding justices…", then a line per fixture. The operator wants a
**progress bar** in that card instead, so a multi-minute reset reads as visible progress.

The `/admin/dev-fixture-state` JSON endpoint the card polls is plumbing, not something
to watch. The bar should be driven from the same `ResetProgress` record (`step`, `completed`,
`total`) the text line already uses.

Related: `2026-08-20-reset-has-no-timeout-or-progress.md` (the timeout and observability
half of the same complaint).
