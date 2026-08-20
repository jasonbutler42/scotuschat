---
created: 2026-08-20T00:00:00.000Z
title: Reset error copy asserts possible DB corruption in cases where the code knows better
area: ui
severity: minor
files:
  - app/src/routes/admin/+page.server.ts (RESET_MID_ERROR, resetToFixture action, ~lines 190-266)
  - .planning/milestones/v1.7-phases/43-dev-only-reset-to-fixture/ (the locked two-copy UI-SPEC)
---

## Problem

Found 2026-08-20 during the Phase 48-10 checkpoint. The operator clicked
"Reset to fixture" and saw:

> Reset failed partway through — the database may be in an inconsistent state.
> Check server logs before retrying.

The reset had in fact **fully succeeded**. `.dev-logs/api-out.log` recorded
`POST /api/admin/dev/reset-to-fixture HTTP/1.1" 200 OK`, and the database was
verified to be in exactly the correct post-reset state: all four fixtures
present with the right statuses, tiers, one AdminJob each, and the complete
birth-plus-transition `argument_status_log` chain.

`RESET_MID_ERROR` is one of only two error strings the Phase 43 UI-SPEC allows,
and the action returns it for **every** failure mode:

- any thrown fetch (network failure or timeout)
- any non-2xx status
- a body that fails to parse as JSON
- a parsed `fixtures` array whose length is not exactly 4

So the string cannot distinguish "nothing was deleted" from "writes may be
partial" from "the work succeeded but the client stopped listening." Its own
docstring already concedes half of this:

> The backend's 503 corpus-missing case also lands on RESET_MID_ERROR even
> though nothing was actually deleted (the backend pre-flights the corpus check
> before the TRUNCATE)

Asserting probable data corruption when the code has no basis for the claim is
worse than a generic failure message: it sends the operator to inspect a
database that is fine, and it would train them to disbelieve the warning on the
day it is real.

## Why it is not simply a copy fix

The two-string set is **locked** by `43-UI-SPEC.md`'s Copywriting Contract
("No third variant is ever returned"). Widening it is a deliberate UI-SPEC
amendment, not a drive-by edit — hence a todo rather than an in-flight change.

## Suggested direction

1. Amend the UI-SPEC to permit a third state distinguishing *pre-flight refusal
   / nothing deleted* from *possible partial write*. The backend already knows
   which it is; only the frontend flattens them.
2. Better: on any failure, have the action re-read fixture state before
   asserting anything, and report what it actually found. The reset endpoint is
   dev-only and idempotent, so a verification read is cheap.
3. At minimum, log the discriminating reason to `.dev-logs/app-err.log`. Today
   every `fail()` branch in `resetToFixture` is silent, which is precisely why
   nothing appeared in the logs when this fired — the message says "check server
   logs" and the server logs contain nothing about it.

## Related

- [[2026-08-20-reset-has-no-timeout-or-progress]] — the probable trigger here
