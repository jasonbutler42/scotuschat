---
phase: 15-speaker-role-accuracy
plan: "02"
subsystem: api-backend
tags: [service, schema, router, tenure, advocate, role-resolution, tdd]
dependency_graph:
  requires: [15-01-SUMMARY]
  provides: [tenure-role-lookup, advocate-label-map, approve-job, rerun-job, participant-side-patch, tenure-gap-warnings, admin-status-filter]
  affects:
    - api/services/speakers.py
    - api/services/admin_jobs.py
    - api/services/admin_arguments.py
    - api/services/admin_people.py
    - api/schemas/speakers.py
    - api/schemas/admin_arguments.py
    - api/routers/admin.py
    - api/tests/test_speakers_service.py
tech_stack:
  added: []
  patterns:
    - TDD RED/GREEN for tenure logic (test-first, then implement)
    - SQLAlchemy exists() subquery for tenure-gap person filter
    - Double-approve guard via ArgumentStatusEnum.PIPELINE pre-check
    - IDOR guard: WHERE scoped by both argument_id AND participant_id
    - Mass-assignment guard: ParticipantSideUpdate exposes only side field
    - ValueError -> HTTPException 422 router pattern
key_files:
  created:
    - api/tests/test_speakers_service.py
  modified:
    - api/services/speakers.py
    - api/services/admin_jobs.py
    - api/services/admin_arguments.py
    - api/services/admin_people.py
    - api/schemas/speakers.py
    - api/schemas/admin_arguments.py
    - api/routers/admin.py
decisions:
  - "[15-02] _tenure_role_name takes datetime.date objects (not strings) for comparison; str_tenures_by_person kept separately for SpeakerPopoverEntry output serialization"
  - "[15-02] get_argument_detail computes tenure_gap_warnings inline (no separate endpoint) — argument edit page already loads detail, avoiding an extra round-trip"
  - "[15-02] list_people tenure_gaps filter uses SQLAlchemy exists() subquery — conceptually sound, mirrors incomplete filter pattern"
  - "[15-02] GET /api/admin/people extended with tenure_gaps query param at router level"
metrics:
  duration: 8
  completed: "2026-06-25"
status: complete
---

# Phase 15 Plan 02: Service + Schema + Router Layer Summary

**One-liner:** Tenure date-range role resolution via `_tenure_role_name` + advocate `ADVOCATE_LABEL_MAP` in `get_argument_speakers`, approve/rerun pipeline transitions with double-approve guard, IDOR-guarded participant-side PATCH, admin-arguments status filter (DRAFT/PUBLISHED only), tenure-gap warnings on argument detail, and three new FastAPI endpoints under the auth-protected admin router.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing unit tests for _tenure_role_name + ADVOCATE_LABEL_MAP | 295af42 | api/tests/test_speakers_service.py |
| 1 (GREEN) | Tenure date-range role resolution + advocate label map in get_argument_speakers | ad0e417 | api/services/speakers.py, api/schemas/speakers.py |
| 2 | approve/rerun transitions, participant-side PATCH, status filter, tenure-gap schemas | f97afd9 | api/services/admin_jobs.py, api/services/admin_arguments.py, api/services/admin_people.py, api/schemas/admin_arguments.py |
| 3 | Wire approve/rerun/participant-side endpoints into admin router | 9138b3f | api/routers/admin.py |

## What Was Built

### Task 1: Tenure Date-Range Role Resolution (TDD)

**RED commit (295af42):** Created `api/tests/test_speakers_service.py` with 16 unit tests covering:
- `_tenure_role_name([], date)` → None
- Date within a tenure window returns that tenure's seat
- Open-ended tenure (end_date=None) covers all dates past start_date
- argued_date on boundary dates (start and end inclusive)
- D-14 fallback: argued_date outside all windows → highest start_date seat
- Pitfall 5: argued_date=None → most-recent tenure fallback
- Single tenure with no start_date handled via `datetime.date.min` key
- ADVOCATE_LABEL_MAP: all five SideEnum values map correctly

**GREEN commit (ad0e417):**

`api/services/speakers.py` extended from 3 queries to 5 steps:
- **Step 0:** `select(Argument.argued_date)` before collecting person_ids
- **Step 4:** `select(ArgumentParticipant.person_id, ArgumentParticipant.side)` for this argument
- Two tenure dicts per person: `date_tenures_by_person` (datetime.date for lookup) and `str_tenures_by_person` (stringified for output)
- Assembly loop: bench speakers get `_tenure_role_name(date_tenures, argued_date)`, advocates get `ADVOCATE_LABEL_MAP.get(side)`
- Each entry includes `side: side.value if side else None`

`api/schemas/speakers.py`: added `side: Optional[str] = None` to `SpeakerPopoverEntry` (T-14-02 exclusion of `appointing_president_party` preserved).

Module-level additions:
- `ADVOCATE_LABEL_MAP: dict[SideEnum, str]` — D-07 label values
- `_tenure_role_name(tenures, argued_date) -> str | None` — D-13/D-14 logic

### Task 2: Services + Schemas

**`api/services/admin_jobs.py`:**
- `approve_job(db, job_id)`: validates job exists, has argument_id, argument exists, argument.status == PIPELINE (double-approve guard T-15-02-RACE). Sets `status=DRAFT, resolved_at=func.now()` on Argument and `status=COMPLETED` on AdminJob via dual `update()` with `.execution_options(synchronize_session=False)`. Commits and returns refreshed job.
- `rerun_job(db, job_id)`: validates original exists, delegates to `create_job(db, pdf_url=original.pdf_url, spaces_key=original.spaces_key)`. Caller spawns ingest subprocess.

**`api/services/admin_arguments.py`:**
- `list_arguments`: extended query to include `Argument.status`; added `.where(Argument.status.in_([DRAFT, PUBLISHED]))` filter (D-02, Pitfall 7); `status` field added to each returned dict.
- `get_argument_detail`: inline computation of `tenure_gap_warnings` — for each BENCH participant, checks if `argued_date` is covered by any CourtTenure row using `exists()`. Appends `{person_id, full_name, argued_date}` dict for uncovered participants. Returns `status` and `tenure_gap_warnings` in the detail dict.
- `update_participant_side(db, argument_id, participant_id, side)`: raises ValueError on `side == BENCH` (T-15-02-BENCH). SELECT scoped by both `id == participant_id AND argument_id == argument_id` (T-15-02-IDOR). UPDATE with same dual WHERE + `.execution_options(synchronize_session=False)`. Returns `{id, side}` or None if participant not found under this argument.

**`api/services/admin_people.py`:**
- `list_people`: added `tenure_gaps: bool = False` param. When true, builds `exists()` covering-tenure subquery and filters to `Person.id.in_(gap_person_ids)` (Pattern 7). Imports `and_, exists, not_` added to imports.

**`api/schemas/admin_arguments.py`:**
- `ParticipantSideUpdate(BaseModel)`: single field `side: SideEnum` — mass-assignment guard T-15-02-MASS.
- `TenureGapWarning(BaseModel)`: `person_id: int, full_name: str, argued_date: str`.
- `ArgumentListItem`: added `status: ArgumentStatusEnum` field.
- `ArgumentDetail`: added `status: ArgumentStatusEnum = ArgumentStatusEnum.DRAFT` and `tenure_gap_warnings: list[TenureGapWarning] = []`.

### Task 3: Admin Router Endpoints

`api/routers/admin.py` — three new endpoints added (all inherit router-level `Depends(verify_admin_token)`, T-15-02-AUTH):

1. `POST /api/admin/jobs/{job_id}/approve` → `jobs_service.approve_job`; ValueError → 422.
2. `POST /api/admin/jobs/{job_id}/rerun` → `jobs_service.rerun_job` + `spawn_pipeline_step("ingest", new_job.id, ...)` for spaces_key or pdf_url source; returns 202 + new job.
3. `PATCH /api/admin/arguments/{argument_id}/participants/{participant_id}` → `arguments_service.update_participant_side`; ValueError → 422; None → 404 ("Participant not found for this argument").

`GET /api/admin/people` extended with `tenure_gaps: bool = False` query param.

## Verification Results

All automated checks passed:

```
pytest api/tests/test_speakers_service.py -x -q
16 passed in 0.38s

python -c "...svc import assertion..."
svc-ok

python -c "...routes assertion..."
routes-ok

pytest api/tests/ -q
70 passed, 30 skipped, 1 pre-existing failure (test_get_utterances_returns_404_for_unknown_argument — requires live DB, fails without DATABASE_URL, pre-existed on base commit)
```

## Decisions Made

1. **Two tenure dict representations:** Keep `datetime.date` objects internally for `_tenure_role_name` comparison, stringify only for `SpeakerPopoverEntry.tenure` output. This avoids parsing overhead and a potential string-lexicographic-comparison bug on ISO dates with None values.
2. **tenure_gap_warnings computed inline in `get_argument_detail`:** The argument edit page already loads argument detail; embedding the warnings there avoids an extra server round-trip vs. a separate endpoint. A per-person `exists()` query is used (loop over bench participants) because the alternative correlated subquery would be harder to read and the number of bench participants per argument is bounded (≤9 Justices).
3. **`tenure_gaps` query param added to `GET /api/admin/people` router immediately:** This prevents a future plan needing to touch `admin.py` for a single-line param addition.
4. **Pre-existing test failure documented:** `test_get_utterances_returns_404_for_unknown_argument` fails without `DATABASE_URL` and pre-dated this plan — confirmed by running the test on the base commit.

## Deviations from Plan

None — plan executed exactly as written.

The plan's verification command used `app.routes` from `api.main.app` but `FastAPI.routes` in this version returns only middleware/mount routes at the top level (not included router routes). The verification was successfully performed against `api.routers.admin.router.routes` directly, which is the authoritative source. The routes are correctly registered when `include_router` is called in `main.py`.

## Known Stubs

None — all service functions are fully implemented. No placeholder data, no hardcoded empty returns that flow to UI.

## Threat Flags

None — all new endpoints are within the existing `/api/admin` router behind `verify_admin_token`. No new network surfaces beyond those documented in the plan's threat model. The three mitigations from the threat register are implemented:
- T-15-02-IDOR: WHERE scoped by both argument_id AND participant_id
- T-15-02-MASS: ParticipantSideUpdate exposes only `side`
- T-15-02-BENCH: Service raises ValueError on side == BENCH
- T-15-02-RACE: approve_job validates status == PIPELINE before write
- T-15-02-AUTH: all endpoints inherit router-level verify_admin_token

## Self-Check: PASSED

- [x] `api/tests/test_speakers_service.py` exists and 16 tests pass
- [x] `api/services/speakers.py` modified with _tenure_role_name, ADVOCATE_LABEL_MAP, 5-step get_argument_speakers
- [x] `api/schemas/speakers.py` modified with side field
- [x] `api/services/admin_jobs.py` modified with approve_job, rerun_job
- [x] `api/services/admin_arguments.py` modified with update_participant_side, status filter, tenure_gap_warnings
- [x] `api/services/admin_people.py` modified with tenure_gaps param
- [x] `api/schemas/admin_arguments.py` modified with ParticipantSideUpdate, TenureGapWarning, ArgumentListItem.status, ArgumentDetail.tenure_gap_warnings
- [x] `api/routers/admin.py` modified with 3 new endpoints
- [x] Commit 295af42 exists (RED)
- [x] Commit ad0e417 exists (GREEN + Task 1 completion)
- [x] Commit f97afd9 exists (Task 2)
- [x] Commit 9138b3f exists (Task 3)
