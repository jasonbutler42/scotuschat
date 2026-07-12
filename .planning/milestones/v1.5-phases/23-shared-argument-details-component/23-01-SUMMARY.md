---
phase: 23-shared-argument-details-component
plan: "01"
subsystem: backend
tags: [api, schemas, services, parse-stats, argument-metadata]
status: complete

dependency_graph:
  requires: []
  provides:
    - ParseStats.bench_count/advocate_count/total_speaker_count/case_name/argued_date/primary_docket/question_number
    - MetadataUpdate.question_number
    - ArgumentDetail.question_number
    - get_job parse_stats dict with 9 keys
    - update_argument_metadata persisting question_number
    - get_argument_detail returning question_number
  affects:
    - api/schemas/admin_jobs.py
    - api/schemas/admin_arguments.py
    - api/services/admin_jobs.py
    - api/services/admin_arguments.py

tech_stack:
  added: []
  patterns:
    - "Defensive JSONB read: (cover_metadata or {}).get(key)"
    - "Guarded int() parse: try/except ValueError → skip (T-23-02)"
    - "Optional fields defaulting to None — backward compat preserved"

key_files:
  created: []
  modified:
    - api/schemas/admin_jobs.py
    - api/schemas/admin_arguments.py
    - api/services/admin_jobs.py
    - api/services/admin_arguments.py

decisions:
  - "cover_metadata fields (case_name, argued_date, primary_docket) passed through ParseStats directly, not as nested dict — matches flat TS interface shape"
  - "speaker_count retained alongside total_speaker_count for backward compat with polling TS interface (ParseStats.speaker_count still returned)"
  - "question_number sourced from Argument.question_number column (NOT cover_metadata — cover extractor writes only 3 keys)"
  - "MetadataUpdate.question_number accepted as Optional[str] free text; service parses to int via guarded try/except (PJOB-06)"
  - "SideEnum.BENCH used for bench_count; side != SideEnum.BENCH for advocate_count (legacy ADVOCATE value included in advocate count)"

metrics:
  duration: "2m"
  completed_date: "2026-07-02"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 4
---

# Phase 23 Plan 01: Backend Schema and Service Expansion Summary

**One-liner:** Expanded ParseStats with bench/advocate/total speaker counts and cover_metadata fields; added question_number to MetadataUpdate and ArgumentDetail; wired get_job and update_argument_metadata service functions to populate and persist these fields.

## What Was Built

### Task 1 — Schema Changes (committed 23351d00)

**`api/schemas/admin_jobs.py` — ParseStats expansion:**
- `utterance_count: int` and `speaker_count: int` retained (backward compat)
- Added Optional fields: `bench_count`, `advocate_count`, `total_speaker_count`, `case_name`, `argued_date`, `primary_docket`, `question_number` — all default None

**`api/schemas/admin_arguments.py` — Argument schemas:**
- `MetadataUpdate` gains `question_number: Optional[str] = None` (free-text input, PJOB-06; service parses to int)
- `ArgumentDetail` gains `question_number: Optional[int] = None` (return field, PJOB-07)
- `MetadataUpdate` docstring updated: allow-list now explicitly includes `question_number` alongside `case_name`, `source_docket`, `argued_date` (T-23-01 mass-assignment discipline)

### Task 2 — Service Changes (committed 508ec6a3)

**`api/services/admin_jobs.py` — get_job expansion:**
- Imported `SideEnum` from `api.models.models`
- Added `bench_count` COUNT query: `ArgumentParticipant.side == SideEnum.BENCH` + `person_id.isnot(None)` scoped to `job.argument_id`
- Added `advocate_count` COUNT query: `ArgumentParticipant.side != SideEnum.BENCH` + `person_id.isnot(None)` (legacy ADVOCATE value included)
- Added `total_speaker_count = bench_count + advocate_count`
- Added `Argument.cover_metadata, Argument.question_number` SELECT via `.one_or_none()`
- `cover_metadata` read defensively: `(arg_row.cover_metadata or {})` guards against None JSONB
- parse_stats dict now has 9 keys: `utterance_count`, `speaker_count`, `bench_count`, `advocate_count`, `total_speaker_count`, `case_name`, `argued_date`, `primary_docket`, `question_number`

**`api/services/admin_arguments.py` — two functions updated:**
- `update_argument_metadata`: adds `question_number` to `values_to_set` when `body.question_number` is provided and non-empty, guarded by `try/except ValueError` that silently skips invalid input (T-23-02 DoS guard)
- `get_argument_detail`: return dict gains `"question_number": argument.question_number`

## Deviations from Plan

None — plan executed exactly as written.

## Threat Mitigations Applied

| Threat ID | Status | Implementation |
|-----------|--------|----------------|
| T-23-01 | Mitigated | MetadataUpdate allow-list explicitly documented: {case_name, source_docket, argued_date, question_number}. No other Argument/Case field writable. |
| T-23-02 | Mitigated | `int(body.question_number)` wrapped in `try/except ValueError` — silently skips non-numeric input, never raises 500 |
| T-23-03 | Deferred to 23-03 | argument_id derived server-side in Plan 23-03 SvelteKit action; existing 404 guard in metadata endpoint unchanged |

## Known Stubs

None — this plan adds no UI; all changes are schema/service-layer additions.

## Threat Flags

None — no new network endpoints, auth paths, or file access patterns introduced. All changes are additions to existing protected endpoints.

## Self-Check

Task commits:
- 23351d00: feat(23-01): expand ParseStats schema and add question_number to argument schemas
- 508ec6a3: feat(23-01): populate expanded parse_stats in get_job; persist question_number in update_argument_metadata

Verification results:
- `ParseStats.model_fields` contains all 9 fields: PASSED
- `MetadataUpdate.model_fields` contains `question_number`: PASSED
- `ArgumentDetail.model_fields` contains `question_number`: PASSED
- `get_job` injects 9-key parse_stats dict: PASSED (ast.parse + import check)
- `update_argument_metadata` writes `question_number` with guarded int(): PASSED
- `get_argument_detail` returns `question_number`: PASSED
- No `Base.metadata.create_all` introduced: PASSED
- No new Alembic migration (Argument.question_number column pre-exists): CONFIRMED
