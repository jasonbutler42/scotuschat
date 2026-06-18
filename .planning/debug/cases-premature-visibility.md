---
status: resolved
trigger: "Cases should only appear in /cases/ after resolve is complete with real case metadata. Newly ingested arguments appear in /cases/ before resolve completes with placeholder titles like 'Pending review (job 3)' and metadata like 'No. job-3 · Argued June 17, 2026 · Question 1'."
created: 2026-06-17T00:00:00Z
updated: 2026-06-18T00:00:00Z
resolved_by: "07-08-PLAN — Alembic migration 0004 added arguments.resolved_at column; get_cases() gates on resolved_at IS NOT NULL; both resolve paths (operator-confirmed and all-auto-resolved) stamp resolved_at on completion (commits 43b8f88, 9543a3c)"
---

## Current Focus

hypothesis: CONFIRMED — two cooperating defects:
  1. The pipeline ingest step creates Case + Argument + CaseArgument rows immediately (with synthetic placeholder metadata: docket="job-{N}", case_name="Pending review (job N)", argued_date=today) and there is no "resolved" or "published" flag on those rows.
  2. The /cases/ list API query (api/services/cases.py get_cases) performs a simple JOIN with WHERE is_lead=TRUE and no filter for resolve completion. Every Case row that has a linked lead CaseArgument is returned, including rows with placeholder values.

test: read api/services/cases.py (confirmed no filter), api/models/models.py (confirmed no resolved_at/is_published column), pipeline/commands/ingest.py (confirmed placeholder row creation at ingest time), grep for resolved_at/is_published (zero hits in api/ and pipeline/).
expecting: root cause confirmed — no column to filter on, no filter applied.
next_action: return diagnosis to caller

## Symptoms

expected: Cases only appear in /cases/ after resolve is complete with real case metadata (docket number, argued date, case title)
actual: Newly ingested arguments appear in /cases/ before resolve completes. They show up with title "Pending review (job 3)" and metadata "No. job-3 · Argued June 17, 2026 · Question 1"
errors: none (application is functioning — this is a visibility/filtering bug)
reproduction: Ingest a new argument via the pipeline runner UI. Navigate to /cases/ before resolve completes.
started: Observed during Phase 07 UAT (gap item in 07-UAT.md — no specific UAT test number)

## Eliminated

- hypothesis: Placeholder values written only during an intermediate step, not persisted until resolve
  evidence: pipeline/commands/ingest.py line 164 explicitly persists case_name="Pending review (job {job_id})", docket="job-{job_id}", argued_date=date.today() into the cases + arguments tables inside the get_session() block that commits on clean exit. These are durable in postgres from the moment ingest completes (before parse or resolve run).
  timestamp: 2026-06-17

- hypothesis: A resolved_at, is_published, or is_resolved column exists on Case or Argument but is not being filtered
  evidence: api/models/models.py defines Case with only (id, docket_number, docket_number_norm, case_name, term_year, slug); Argument with only (id, argued_date, question_number). No status or visibility field of any kind. grep for resolved_at/is_published/is_resolved across api/ and pipeline/ returned zero matches. All three Alembic migrations (0001, 0002, 0003) contain no such column. The schema gap is complete — the concept does not exist anywhere in the data model.
  timestamp: 2026-06-17

## Evidence

- timestamp: 2026-06-17
  checked: api/routers/cases.py
  found: GET /cases calls cases_service.get_cases(db) with no parameters — no filter argument is passed.
  implication: No filtering can happen at the router level.

- timestamp: 2026-06-17
  checked: api/services/cases.py get_cases()
  found: Query is SELECT Case, Argument JOIN CaseArgument WHERE CaseArgument.is_lead == True ORDER BY argued_date DESC. No status, resolved_at, or any other visibility filter.
  implication: Every Case that has a lead CaseArgument is returned. Ingest creates that CaseArgument immediately, so every ingested job appears in /cases/ the instant ingest completes.

- timestamp: 2026-06-17
  checked: api/models/models.py — Case model (Table 4), Argument model (Table 5)
  found: Case has columns: id, docket_number, docket_number_norm, case_name, term_year, slug. Argument has: id, argued_date, question_number. Neither model has any status, resolved_at, is_published, or visibility field.
  implication: There is no column to filter on. Even if the query wanted to filter, no such field exists.

- timestamp: 2026-06-17
  checked: pipeline/commands/ingest.py _derive_metadata_from_key() and _run_ingest_inner() Step 5
  found: When job-driven (--job-id set), _derive_metadata_from_key() at line 164 sets case_name="Pending review (job {job_id})", primary_docket="job-{job_id}", argued_date=date.today(). These values are written into the cases and arguments tables inside the get_session() block (Step 5, lines 308–379) which commits on clean __aexit__. The AdminJob is then marked COMPLETED (Step 6). At no point does ingest set a placeholder flag or suppress visibility.
  implication: The "Pending review" row is durable in postgres as soon as ingest completes — well before parse or resolve run.

- timestamp: 2026-06-17
  checked: pipeline/commands/resolve.py — full resolve flow
  found: Resolve updates utterances.person_id, argument_participants.person_id, and PipelineRun.status. It writes discrepancies to AdminJob and sets AdminJob.status=PAUSED or COMPLETED. Critically: resolve never updates Case.case_name, Case.docket_number, Argument.argued_date, or any "publish" flag. Placeholder metadata is never overwritten by the resolve step.
  implication: Even after resolve completes successfully, the Case row still reads case_name="Pending review (job N)" and docket="job-N" unless something else updates it. Resolve does not touch case metadata at all.

- timestamp: 2026-06-17
  checked: app/src/routes/cases/+page.server.ts
  found: SvelteKit load function calls fetch(`${FASTAPI_BASE_URL}/cases`) and returns data.cases directly. No client-side filtering.
  implication: Every row returned by the API appears in the UI. The bug is entirely in the API layer (no filter) and data model (no flag to filter on).

- timestamp: 2026-06-17
  checked: alembic/versions/ (all three migrations: 0001, 0002, 0003)
  found: No migration adds resolved_at, is_published, or any visibility column to cases or arguments tables. The schema was never designed with a publish gate.
  implication: The absence of a filter is not an oversight in the query — it is a gap in the data model. A migration is required to add a visibility column before the query can be fixed.

## Resolution

root_cause: >
  The /cases/ list query in api/services/cases.py has no filter for resolve completion because no
  such column exists on the Case or Argument models. The ingest pipeline (pipeline/commands/ingest.py)
  creates Case + Argument + CaseArgument rows with synthetic placeholder values
  (case_name="Pending review (job N)", docket="job-{N}", argued_date=today) and commits them
  immediately at ingest time, before parse or resolve run. The resolve step (pipeline/commands/resolve.py)
  never updates case metadata and never sets any "published" or "resolved" flag on Case or Argument.
  The result is that every ingested job is visible in /cases/ from the moment ingest completes,
  carrying placeholder text until a Phase 8 metadata-edit UI (which does not yet exist) overwrites it.

fix: (not applied — diagnose-only mode)
verification: (not applied — diagnose-only mode)
files_changed: []
