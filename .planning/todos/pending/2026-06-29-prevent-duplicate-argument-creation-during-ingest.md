---
created: 2026-06-29T16:19:39.209Z
title: Prevent duplicate argument creation during ingest
area: pipeline
resolves_phase: 19
files:
  - pipeline/commands/ingest.py:351-356
  - pipeline/commands/parse.py
  - alembic/versions/0001_initial_schema.py:112-118
  - app/src/routes/admin/pipeline/+page.svelte
---

## Problem

`ingest.py` always creates a new `Argument` row (lines 351–356) without checking whether
a matching argument already exists. The `arguments` table has no unique constraint — only
`cases.docket_number` is unique. Re-running ingest for the same case produces a second
argument row, silently orphaning the first one's utterances and participants.

The natural unique key for a SCOTUS oral argument is:
`(primary_docket, argued_date, question_number)` — a case cannot be argued twice on
the same date for the same question. This maps to a join across `case_arguments` and
`cases`.

**Complication:** In job-driven mode (admin UI), `argued_date` defaults to today and
`primary_docket` defaults to `job-{job_id}` (synthetic) at ingest time. The real
docket and date are only known after the cover extractor runs during the parse step.
So a pre-ingest duplicate check using real metadata is not possible from the UI.

## Solution

Two-part approach:

1. **DB constraint:** Add a unique index on `(case_id, argued_date, question_number)`
   in `case_arguments` (via a new Alembic migration) so the database rejects exact
   duplicates at the data layer regardless of how they're created.

2. **UI guard:** On the pipeline start page, after the operator enters a URL or selects
   a file, check whether an argument with a matching docket + date already exists and
   surface a warning before the run begins. This requires the cover extractor to either
   (a) run as a pre-flight check on the PDF before committing DB records, or (b) the UI
   presents a post-parse duplicate warning after real metadata is extracted and lets the
   operator confirm or cancel before the resolve step proceeds.

The DB constraint is the reliable safety net. The UI guard is the operator-friendly
experience layer on top.
