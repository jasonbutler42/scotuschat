---
name: is-justice-schema-decision
description: Decision to add explicit is_justice boolean to people table rather than inferring bench/non-bench status from tenure presence
metadata:
  type: project
---

Add an explicit `is_justice` boolean column to the `people` table.

**Why:** The system already treats bench and non-bench people differently (Justice fields: tenure, appointment, court role; Advocate fields: per-argument side). The distinction is currently implicit — a person is treated as a Justice if they have tenure records. This is fragile: a newly created Justice with no tenures yet appears as non-bench, and a retired Justice arguing as an advocate would be ambiguous.

**How to apply:** Alembic migration adds `is_justice BOOLEAN NOT NULL DEFAULT FALSE` to `people`. Backfill sets `is_justice = TRUE` for any person with at least one tenure record. The people editor gates Role, Court Tenure, and Appointment sections on this flag. Future schema or UI decisions about person type use `is_justice` as the source of truth — not tenure presence.

An enum (`JUSTICE` / `ADVOCATE`) was considered but deferred — a boolean is sufficient for current needs and easier to migrate later if additional person types emerge.
