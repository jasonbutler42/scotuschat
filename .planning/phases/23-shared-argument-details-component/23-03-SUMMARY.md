---
phase: 23-shared-argument-details-component
plan: "03"
subsystem: frontend/wiring
tags: [sveltekit, svelte5, form-actions, parse-stats, argument-metadata, admin-ui]
status: complete

dependency_graph:
  requires:
    - "23-01-PLAN.md (ParseStats expanded; MetadataUpdate.question_number; ArgumentDetail.question_number)"
    - "23-02-PLAN.md (ArgumentDetailsCard.svelte component)"
  provides:
    - "saveJobMetadata SvelteKit action: persists dockets/question_number/argued_date to linked argument"
    - "savedValues/hints props constructed in load() and returned to page"
    - "ArgumentDetailsCard wired as the argument details form on pipeline/[job_id]"
    - "Expanded parse stat card: Utterances + Bench/Advocate/Total + Case name + Argued + Docket pill + Question number"
    - "Ingest Source file row removed"
  affects:
    - "app/src/routes/admin/pipeline/[job_id]/+page.server.ts"
    - "app/src/routes/admin/pipeline/[job_id]/+page.svelte"

tech_stack:
  added: []
  patterns:
    - "Non-null assertion (data.savedValues!) inside {#if data.argument != null} guard — load() contract guarantees non-null"
    - "saveJobMetadata two-step: fetch job → derive argument_id server-side → PATCH metadata endpoint (T-23-03-01 IDOR guard)"
    - "docket[] array via FormData.getAll — pill serialization (D-05)"
    - "Parse stat fields read from ps.* (cover_metadata passthrough) not data.argument.* (Pitfall 7 guard)"

key_files:
  created: []
  modified:
    - "app/src/routes/admin/pipeline/[job_id]/+page.server.ts"
    - "app/src/routes/admin/pipeline/[job_id]/+page.svelte"

decisions:
  - "Non-null assertion used for savedValues!/hints! inside the {#if data.argument != null} guard — TypeScript cannot narrow through the conditional but the load() contract guarantees non-null when argument is set"
  - "Old saveMetadata action retained in +page.server.ts (harmless; ArgumentDetailsCard only targets saveJobMetadata via its action prop)"
  - "Parse stat case_name/argued_date/primary_docket/question_number sourced from ps.* (cover_metadata passthrough from Plan 23-01) — never from data.argument.* to prevent PJOB-12 source mismatch"

metrics:
  duration: "5m"
  completed_date: "2026-07-02"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
---

# Phase 23 Plan 03: Pipeline Job Detail Page Wiring Summary

**One-liner:** Wired ArgumentDetailsCard into /admin/pipeline/[job_id] with saveJobMetadata action, savedValues/hints from load(), expanded parse stat card (8 fields, N/A fallbacks), and removal of the ingest Source file row.

## What Was Built

### Task 1 — +page.server.ts changes (committed 8a9a49d7)

**`ArgumentPreview` interface:**
- Added `question_number: number | null`

**`load()` additions:**
- Constructs `savedValues` after the argument fetch: `dockets` from `source_docket` wrapped in array, `question_number` as string or `''`, `argued_date` as ISO YYYY-MM-DD slice
- Constructs `hints` from `cover_metadata`: `dockets` from `primary_docket`, `question_number` from `Argument.question_number` (not cover_metadata — Pitfall 3 guard), `argued_date` and `case_name` from JSONB
- Both return `null` when `argument` is null (rendered conditionally in the page)
- Returns `{ ..., savedValues, hints }` alongside existing page data

**`saveJobMetadata` action:**
- Reads `docket[]` via `formData.getAll` (D-05 pill serialization)
- Trims and filters empty strings from dockets array (T-23-03-03)
- Two-step: fetches job to derive `argument_id` server-side (T-23-03-01 IDOR guard — never accepts argument_id from form data)
- Guards: `fail(502)` on job-fetch network error; `fail(400, { saveError, dockets })` when argument_id is null (PJOB-07 — never creates an argument; never calls approve)
- PATCHes `/api/admin/arguments/{argumentId}/metadata` with `source_docket`, `argued_date`, `question_number` (as free-text string — backend parses to int per 23-01)
- Returns `fail(502)` or `fail(422)` with `{ saveError, dockets }` on failure (D-06 pill restore)
- Returns `{ saved: true }` on success

### Task 2 — +page.svelte changes (committed f01958b3)

**Imports:**
- Added `import ArgumentDetailsCard from '$lib/components/ArgumentDetailsCard.svelte'`

**Argument Metadata form → ArgumentDetailsCard (D-02, AEDIT-04):**
- Removed entire old Argument Metadata `<div>/<form>` block (case_name/source_docket/argued_date, action=?/saveMetadata, conditional hints)
- Replaced with `<ArgumentDetailsCard savedValues={data.savedValues!} hints={data.hints!} action="?/saveJobMetadata" form={form} />` inside the existing `{#if data.argument != null}` guard

**ParseStats TS interface expansion (PJOB-10):**
- Added optional fields: `bench_count`, `advocate_count`, `total_speaker_count`, `case_name`, `argued_date`, `primary_docket`, `question_number` (all `? number | null` or `? string | null`)
- Retained existing `utterance_count` and `speaker_count` for backward compat

**Parse stat card rework (PJOB-10/11/12):**
- Utterances: always shown, never N/A
- Bench speakers / Advocate speakers / Total speakers: numeric or italic N/A
- Case name: from `ps.case_name` (cover_metadata passthrough), italic N/A when null
- Argued: `formatDate(ps.argued_date)` (cover_metadata), italic N/A when null
- Docket(s): `ps.primary_docket` as a read-only pill (matching hint pill style), italic N/A when null
- Question number: `ps.question_number` numeric, italic N/A when null
- Removed old `{#if data.argument}` Case name / Argued rows that read from `data.argument.*` (Pitfall 7 fix, PJOB-12)

**Ingest Source file row removal (PJOB-09):**
- Deleted the `{#if step === 'ingest' && (liveJob.original_filename || liveJob.pdf_url)}` block entirely

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Non-null assertion required for savedValues/hints props**
- **Found during:** Task 2 svelte-check verification
- **Issue:** `data.savedValues` and `data.hints` are typed `| null` from load() (null when no argument). TypeScript could not narrow through the `{#if data.argument != null}` conditional, so passing them directly to ArgumentDetailsCard (which does not accept null) produced type errors.
- **Fix:** Used non-null assertion `data.savedValues!` and `data.hints!` inside the guard block, with a comment explaining the load() contract guarantees non-null when `data.argument != null`.
- **Files modified:** `+page.svelte` (same task commit)
- **Commit:** f01958b3

## Threat Mitigations Applied

| Threat ID | Status | Implementation |
|-----------|--------|----------------|
| T-23-03-01 | Mitigated | argument_id derived server-side from job fetch in saveJobMetadata — never read from form data |
| T-23-03-02 | Mitigated | saveJobMetadata never calls approve or any argument-creation endpoint; fail(400) when argument_id is null |
| T-23-03-03 | Mitigated | docket[] values trimmed + empty-filtered before PATCH; source_docket = dockets[0] ?? null |

## Known Stubs

None — ArgumentDetailsCard is fully wired with live savedValues/hints from the server load. The parse stat card reads from the expanded ParseStats fields (provided by Plan 23-01). All data paths are live.

## Threat Flags

None — no new network endpoints, auth paths, or trust boundaries beyond those identified in the plan's threat model. The saveJobMetadata action reuses the existing argument metadata PATCH endpoint.

## Self-Check

Task commits:
- 8a9a49d7: feat(23-03): add saveJobMetadata action, savedValues/hints, question_number to +page.server.ts
- f01958b3: feat(23-03): replace metadata form with ArgumentDetailsCard; expand parse stat card; remove Source file row

Verification results:
- `svelte-check --threshold error` for `+page.server.ts`: 0 errors — PASSED
- `svelte-check --threshold error` for `+page.svelte`: 0 errors — PASSED
- Overall: 788 files, 0 errors — PASSED
- `saveJobMetadata` action present in `+page.server.ts`: CONFIRMED
- `ArgumentDetailsCard` imported and rendered with `action="?/saveJobMetadata"`: CONFIRMED
- Parse stat rows read from `ps.*` (not `data.argument.*`): CONFIRMED (Pitfall 7 guard)
- Ingest Source file row removed: CONFIRMED (grep returns no matches)
- `saveJobMetadata` never creates an argument (no approve call, fail(400) on null argument_id): CONFIRMED
