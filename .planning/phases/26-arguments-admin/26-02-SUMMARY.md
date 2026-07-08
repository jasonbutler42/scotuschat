---
phase: 26-arguments-admin
plan: 02
subsystem: api
tags: [sqlalchemy, pydantic, fastapi, admin]

# Dependency graph
requires:
  - phase: 26-arguments-admin (Plan 01)
    provides: Three-state Argument lifecycle (status-keyed guards) and a populated ArgumentStatusLog audit trail
provides:
  - list_argument_speakers service helper — unified bench+advocate speaker rows with utterance counts and tenure-derived bench roles
  - StatusLogEntry and SpeakerRow Pydantic schemas
  - ArgumentDetail.status_log and ArgumentDetail.speakers response fields
  - ParticipantSideUpdate.title — advocate title writable via the existing participant-update endpoint
affects: [26-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "list_argument_speakers mirrors admin_people.list_resolve_rows_for_job's per-participant row-building shape (bench/advocate branching, tenure prefetch) but is keyed on argument_id directly, not job_id"
    - "Utterance counts computed via one grouped query (group_by(Utterance.person_id)) scoped to the argument, never per-participant, to avoid N+1 (T-26-07)"
    - "Only-write-provided-fields pattern (values_to_set dict built conditionally) reused for update_participant_side.title, mirroring update_argument_metadata"

key-files:
  created: []
  modified:
    - api/services/admin_arguments.py
    - api/schemas/admin_arguments.py
    - api/routers/admin.py
    - api/tests/test_admin_arguments_service.py
    - api/tests/test_admin_arguments_routes.py

key-decisions:
  - "list_argument_speakers is a new, argument-scoped helper (not a reuse of admin_people.list_resolve_rows_for_job, which is job-scoped and includes an editable flag this page doesn't need)"
  - "Bench rows with person_id IS NULL report missing_tenure=False (no person to flag) — mirrors list_resolve_rows_for_job's identical unresolved-row handling rather than treating unresolved as a tenure gap"
  - "title_hint sources the same ArgumentParticipant.title column as title for advocate rows (D-06, Phase 25 precedent) — there is no separate stored 'originally extracted' snapshot"
  - "update_participant_side.title is written only when the caller passes a non-None value, so omitting title in a PATCH never clobbers a previously-saved title"
  - "participants + tenure_gap_warnings retained on ArgumentDetail alongside the new status_log + speakers fields for backward compatibility — Plan 26-04 will decide whether to remove them once the rebuilt edit page ships"

requirements-completed: [AEDIT-01, AEDIT-02, AEDIT-05, AEDIT-06, AEDIT-07]

coverage:
  - id: D1
    description: "list_argument_speakers returns one row per ArgumentParticipant with a correct utterance_count computed via a single grouped query (no N+1)"
    requirement: "AEDIT-05"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_arguments_service.py#test_list_argument_speakers_bench_advocate_and_utterance_counts"
        status: pass
    human_judgment: false
  - id: D2
    description: "Bench rows carry bench_role/argument_role when a CourtTenure covers argued_date, or missing_tenure=True + person_edit_href when none does"
    requirement: "AEDIT-07"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_arguments_service.py#test_list_argument_speakers_bench_advocate_and_utterance_counts"
        status: pass
    human_judgment: false
  - id: D3
    description: "Advocate rows carry argument_role from ADVOCATE_LABEL_MAP and title/title_hint from ArgumentParticipant.title"
    requirement: "AEDIT-06"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_arguments_service.py#test_list_argument_speakers_bench_advocate_and_utterance_counts"
        status: pass
    human_judgment: false
  - id: D4
    description: "get_argument_detail returns status_log (oldest-first ArgumentStatusLog rows) and speakers (full list_argument_speakers output)"
    requirement: "AEDIT-01"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_arguments_service.py#test_get_argument_detail_includes_status_log_and_speakers"
        status: pass
    human_judgment: false
  - id: D5
    description: "update_participant_side persists title only when provided (leaves it unchanged when omitted) and still rejects side==BENCH"
    requirement: "AEDIT-06"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_arguments_service.py#test_update_participant_side_persists_title_for_advocate"
        status: pass
    human_judgment: false
  - id: D6
    description: "PATCH /arguments/{id}/participants/{id} accepts {side, title}, persists both, and returns the persisted title"
    requirement: "AEDIT-02"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_arguments_routes.py#test_update_participant_route_persists_title_for_advocate"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-08
status: complete
---

# Phase 26 Plan 02: Argument speakers + status log data contract Summary

**New `list_argument_speakers` service helper backing `ArgumentDetail.status_log` and `ArgumentDetail.speakers` (unified bench+advocate rows with utterance counts), plus a writable advocate `title` on the existing participant-update endpoint.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 2 completed
- **Files modified:** 5 (3 source, 2 test)

## Accomplishments
- New `list_argument_speakers(db, argument_id)` in `admin_arguments.py` returns one unified row per `ArgumentParticipant` (bench and advocate), with bench role/missing-tenure derived from `admin_people._bench_role_and_missing_tenure` and advocate role from `speakers.ADVOCATE_LABEL_MAP`
- Utterance counts are computed via a single grouped query (`group_by(Utterance.person_id)`) scoped to the argument — no per-participant N+1 (T-26-07)
- New `StatusLogEntry` and `SpeakerRow` Pydantic models; `ArgumentDetail` now also returns `status_log` (every `ArgumentStatusLog` row, oldest first) and `speakers` (the full `list_argument_speakers` output) alongside the existing `participants`/`tenure_gap_warnings` fields
- `ParticipantSideUpdate` gained an optional `title` field; `update_participant_side` writes it only when provided (non-BENCH participants only) and the PATCH route passes it through and returns the persisted value
- This closes the data-contract gap the rebuilt argument edit page (Plan 26-04) needs: a timestamped status history and a single Speakers table covering every participant with editable advocate titles

## Task Commits

Each task was committed atomically:

1. **Task 1: Add list_argument_speakers helper and StatusLogEntry/SpeakerRow schemas** - `d2e18848` (feat)
2. **Task 2: Wire status_log + speakers into ArgumentDetail; persist advocate title on participant update** - `78ffb1c5` (feat)

**Plan metadata:** committed alongside STATE.md/ROADMAP.md updates (see final commit below)

## Files Created/Modified
- `api/services/admin_arguments.py` - new `list_argument_speakers` helper; `get_argument_detail` now fetches the status log and calls the new helper; `update_participant_side` accepts and conditionally persists `title`
- `api/schemas/admin_arguments.py` - new `StatusLogEntry`/`SpeakerRow` models; `ArgumentDetail.status_log`/`speakers` fields; `ParticipantSideUpdate.title` field
- `api/routers/admin.py` - participant PATCH route passes `body.title` through and returns it
- `api/tests/test_admin_arguments_service.py` - `list_argument_speakers` bench-covered/bench-missing-tenure/advocate/utterance-count tests, `get_argument_detail` status_log+speakers test, `update_participant_side` title-persistence test
- `api/tests/test_admin_arguments_routes.py` - PATCH participant route title-persistence + BENCH-still-rejected test

## Decisions Made
- `list_argument_speakers` is intentionally a new, argument-scoped helper rather than a reuse of the job-scoped `list_resolve_rows_for_job` (different callers, different `editable` semantics)
- An unresolved bench row (`person_id IS NULL`) reports `missing_tenure=False` — mirrors the existing `list_resolve_rows_for_job` convention of not flagging a tenure gap when there's no person to fix
- `title_hint` sources the same `ArgumentParticipant.title` column as `title` (Phase 25 D-06 precedent — no separate extraction snapshot exists)
- `update_participant_side` uses the "only write provided fields" pattern (conditionally building a `values_to_set` dict) so omitting `title` in a PATCH never clobbers a previously-saved title
- `participants`/`tenure_gap_warnings` are retained on `ArgumentDetail` for backward compatibility; Plan 26-04 (frontend rebuild) will decide whether to drop them once the new Speakers section fully replaces their UI usage

## Deviations from Plan

None - plan executed exactly as written. All acceptance criteria (helper signature, new imports, grouped-query utterance count, new schemas and their fields, status-log ordering, title-conditional write, router passthrough) verified via grep after implementation.

## Issues Encountered

None new. As in Plan 26-01, `DATABASE_URL` is not configured in this execution environment (the root `tests/conftest.py` that loads `.env` does not apply to `api/tests/`), so all DB-touching tests in the scoped verification command skip rather than run — this matches the project's established, already-documented test pattern (see `.planning/phases/26-arguments-admin/deferred-items.md`), not a new gap introduced by this plan. The scoped verification command (`test_admin_arguments_service.py test_admin_arguments_routes.py`) passes cleanly: 22 passed, 22 skipped.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

The API now exposes everything the rebuilt argument edit page (Plan 26-04) needs in one response: a full status history and a single unified Speakers list with per-participant utterance counts, bench tenure/missing-tenure state, and an editable advocate title with its extraction hint. No blockers identified for Plan 26-04.

---
*Phase: 26-arguments-admin*
*Completed: 2026-07-08*
