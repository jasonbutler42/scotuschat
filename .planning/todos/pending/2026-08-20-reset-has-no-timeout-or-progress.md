---
created: 2026-08-20T00:00:00.000Z
title: Reset-to-fixture is a multi-minute destructive operation with no timeout, progress, or observability
area: ui
severity: minor
files:

  - app/src/routes/admin/+page.server.ts (resetToFixture action fetch, ~line 237)
  - api/services/admin_dev.py (reset_to_fixture)

audit_acknowledged:
  milestone: v1.8
  at: 2026-09-23
---

## Problem

Found 2026-08-20 during the Phase 48-10 checkpoint, as the probable cause of a
spurious "reset failed" error while the reset actually succeeded.

Measured duration of a real-corpus reset, from the audit rows it wrote:

```
14:15:41  fixture 1 lands (first admin_job created)
14:17:00  fixture 2
14:18:20  fixture 3
14:18:54  fixture 4
14:18:55  approve_job + publish_argument (step 5 state realization)
```

**3m13s of database writes alone**, and that window excludes the corpus
pre-flight, the TRUNCATE, and ConvoKit corpus file loading that happen before
the first row lands. Utterance counts per fixture: 480 / 167 / 157 / 197.

The frontend fetch that drives it:

```ts
res = await fetch(`${FASTAPI_BASE_URL}/api/admin/dev/reset-to-fixture`, {
  method: 'POST',
  headers: { 'X-Admin-Token': ADMIN_TOKEN },
});
```

No `AbortSignal`, no explicit timeout — so it inherits undici's default
`headersTimeout` (300s). Response headers are only sent once the whole handler
finishes, so a reset that runs long enough throws in the client while the server
carries on and commits everything. That produces the exact observed symptom: a
failure message in the UI, a `200 OK` in `.dev-logs/api-out.log`, and a
perfectly consistent database.

There is also no progress signal of any kind. From the operator's side a
three-minute destructive operation is indistinguishable from a hang.

## Phase 48 made this slower

Not the root cause, but it moved the operation closer to the ceiling:

- Plan 48-04 wired `recompute_argument_tier` into all four `admin_jobs` writers,
  so every `approve_job` during state realization now recomputes a tier.
- Plan 48-05 added a birth `ArgumentStatusLog` write plus a tier recompute to
  every import path, so each of the four fixture imports does more work.

Both are correct behaviour. They just make an already-slow dev operation slower,
and nothing in the reset path was sized for it.

## Suggested direction

- Set an explicit, generous timeout on the reset fetch and treat exceeding it as
  its own distinct state ("still running — re-check state before retrying"),
  not as a failure.
- Give the operator progress. The backend already iterates `FIXTURE_SET` in
  declaration order, so per-fixture streaming or a simple polled status is
  tractable.
- Consider whether state realization needs a tier recompute per writer during a
  bulk reseed, or whether one recompute pass at the end would do.

## Related

- [[2026-08-20-reset-error-copy-overclaims-db-corruption]] — what the operator
  actually sees when this fires
