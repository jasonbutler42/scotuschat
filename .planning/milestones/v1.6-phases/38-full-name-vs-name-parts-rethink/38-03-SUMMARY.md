---
phase: 38-full-name-vs-name-parts-rethink
plan: "03"
subsystem: api
tags: [pydantic-v2, fastapi, mass-assignment, sqlalchemy, pytest]

# Dependency graph
requires:
  - phase: 38-full-name-vs-name-parts-rethink
    provides: "api/domain/person_names.py: prepare_person_name, PersonNameError (Plan 01); Person.name_needs_review/name_extraction_metadata columns (Plan 02, migration 0022)"
provides:
  - "api/schemas/admin_people.py: PersonUpdate/PersonCreateRequest with no writable full_name field, extra=\"forbid\" mass-assignment guard, typed NameExtractionMetadata/name_needs_review response fields"
  - "api/services/admin_people.py: create_person/update_person derive full_name exclusively via prepare_person_name; PATCH merges omitted-vs-cleared name parts against stored state; \"name review\" directory indicator/filter (D-12)"
  - "api/schemas/admin_jobs.py: PersonCreate with structured name parts (no full_name), extra=\"forbid\""
  - "api/services/admin_jobs.py: create_person_for_job derives full_name via the same shared helper before the existing job-state/participant-scope IDOR guards"
affects: [38-04, 38-05, 38-06, admin_people, admin_jobs, people-directory-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Writable request schemas use Pydantic v2 ConfigDict(extra=\"forbid\") as the enforcement mechanism for T-38-07 — a client-supplied full_name (or any other undeclared field) is a 422 ValidationError at the schema boundary, not a silently-ignored write, and this is verifiable via model_json_schema()['additionalProperties'] == False without a DB"
    - "PATCH merge-then-validate: a name-part PATCH reads model_fields_set to distinguish omitted-vs-explicitly-cleared fields, merges the touched subset against the person's currently stored parts, then calls prepare_person_name once on the merged result — the same helper enforces the D-09 minimum-data invariant and derives full_name atomically, so no partial/inconsistent state can ever be committed"
    - "An authoritative name-part edit clears Person.name_needs_review but never touches Person.name_extraction_metadata — the review flag reflects resolvable ambiguity, the metadata envelope is an independent, permanent audit trail"

key-files:
  created: []
  modified:
    - api/schemas/admin_people.py
    - api/services/admin_people.py
    - api/schemas/admin_jobs.py
    - api/services/admin_jobs.py
    - api/routers/admin.py
    - api/tests/test_admin_people_schemas_service.py
    - api/tests/test_admin_people.py
    - api/tests/test_admin_jobs_phase25.py
    - api/tests/test_isolation_survives_inner_commit.py

key-decisions:
  - "PersonCreateRequest/PersonUpdate/admin_jobs.PersonCreate all drop full_name as a field entirely (not just stop requiring it) and set extra=\"forbid\" — a posted full_name is a 422 ValidationError, matching D-01's 'full_name is generated, never independently editable' more strongly than silently ignoring an extra key would"
  - "The old local _derive_full_name in admin_people.py (no suffix comma, required both first AND last) was deleted rather than left dead — create_person/update_person/create_person_for_job all now call the one shared api.domain.person_names.prepare_person_name helper (D-01, D-03)"
  - "\"name review\" is surfaced through the EXISTING missing-field pill/filter mechanism (_missing_fields + missing_filters allow-list) rather than a new UI concept, per D-12/D-13's explicit instruction to try the People directory's established attention pattern before adding anything new; it applies to both tabs (bench and advocate), not gated by is_justice"
  - "prepare_person_name is called before the job/participant existence and state checks in create_person_for_job (name validation is pure and side-effect-free, so validating it first is strictly more defensive and does not weaken the existing T-25-01 IDOR guard, which still runs before any Person row is constructed)"
  - "Job mini-create's D-14 provenance-prefill behavior is deferred to Plan 04 (pipeline/import extraction) by design: a job-scoped mini-create has no independent extraction source distinct from the operator's own typed input at this layer, so a freshly created Person via create_person_for_job is unambiguous by construction (name_needs_review=False, name_extraction_metadata=None), matching create_person's behavior"

patterns-established:
  - "model_json_schema()['properties'] and ['additionalProperties'] are the direct, DB-free way to assert a mass-assignment boundary (no full_name property, additionalProperties: False) — used both in this plan's tests and inline during verification"

requirements-completed: []  # PEOPLE-09 spans all 6 plans in this phase; not marked complete until the phase's final plan (38-06), per Plan 01/02 precedent

coverage:
  - id: D1
    description: "PersonCreateRequest/PersonUpdate reject a client-supplied full_name (422) and enforce the D-09 first-or-last minimum via the shared prepare_person_name helper; a valid create/PATCH derives full_name atomically"
    requirement: "PEOPLE-09"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_people_schemas_service.py::test_person_update_rejects_full_name_as_extra_field, test_person_create_request_rejects_full_name_as_extra_field, test_create_person_rejects_missing_first_and_last"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_people.py::test_create_person_rejects_full_name_field, test_create_person_rejects_missing_first_and_last, test_update_person_rejects_full_name_field (real DB via ephemeral scotus_test Postgres)"
        status: pass
    human_judgment: false
  - id: D2
    description: "PATCH merges an omitted name-part field against the person's stored parts (never wiped) while an explicit null/blank is a deliberate clear, re-deriving full_name atomically from the merged result; a merge that would leave neither first nor last is rejected with nothing written"
    requirement: "PEOPLE-09"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_people.py::test_update_person_partial_name_patch_merges_with_stored_parts, test_update_person_explicit_null_clears_name_part, test_update_person_name_edit_rejects_clearing_both_first_and_last"
        status: pass
    human_judgment: false
  - id: D3
    description: "A successful authoritative name-part edit clears Person.name_needs_review but leaves Person.name_extraction_metadata untouched; the People directory 'name review' filter/indicator surfaces flagged rows without gating on is_justice"
    requirement: "PEOPLE-09"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_people.py::test_update_person_authoritative_name_edit_clears_name_needs_review"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_people_schemas_service.py::test_missing_fields_appends_name_review_when_flagged_advocate, test_missing_fields_appends_name_review_when_flagged_bench, test_missing_fields_omits_name_review_by_default"
        status: pass
    human_judgment: false
  - id: D4
    description: "Job mini-create (create_person_for_job) accepts structured name parts, rejects a client full_name (422), and derives full_name via the same shared helper, while preserving all existing authentication, job-state, participant-scope, and same-transaction linkage guards"
    requirement: "PEOPLE-09"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_jobs_phase25.py::test_person_create_rejects_full_name_as_extra_field, test_person_create_accepts_name_parts_without_full_name, test_create_person_for_job_rejects_missing_first_and_last, test_create_person_for_job_validates_participant_before_person_insert"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_jobs_phase25.py::test_create_person_for_job_bench_sets_is_justice_and_participant_side, test_create_person_for_job_advocate_sets_is_justice_false, test_create_person_for_job_rejects_wrong_job_state, test_create_person_for_job_rejects_unknown_raw_speaker_label, test_create_person_for_job_rejects_participant_outside_job_argument (real DB)"
        status: pass
    human_judgment: false

duration: ~70min
completed: 2026-07-27
status: complete
---

# Phase 38 Plan 03: People/Job API Name Authority Enforcement Summary

**PersonUpdate, PersonCreateRequest, and admin_jobs.PersonCreate all drop `full_name` as a writable field (Pydantic `extra="forbid"`, a 422 not a silent no-op), and every create/update write path — including the job-scoped mini-create — derives `full_name` exclusively through the shared `prepare_person_name` helper, with PATCH correctly merging omitted-vs-cleared name parts and clearing `name_needs_review` (never `name_extraction_metadata`) on an authoritative edit.**

## Performance

- **Duration:** ~70 min (includes provisioning an ephemeral, throwaway PostgreSQL 16 instance via `pgserver` for full-suite regression verification — see Issues Encountered)
- **Completed:** 2026-07-27
- **Tasks:** 2
- **Files modified:** 9 (2 schemas, 2 services, 1 router, 4 tests)

## Accomplishments

- `api/schemas/admin_people.py`: `PersonUpdate` and `PersonCreateRequest` no longer declare a `full_name` field at all and both set `model_config = ConfigDict(extra="forbid")` — a client that posts `full_name` gets a 422 `ValidationError`, verified directly via `model_json_schema()['additionalProperties'] == False` and the absence of `full_name` from `['properties']`. Added `NameExtractionMetadata` (typed provenance envelope matching migration 0022's exact JSONB shape) and `name_needs_review`/`name_extraction_metadata` response fields on `PersonDetail`, plus `name_needs_review` on `PersonListItem`.
- `api/services/admin_people.py`: `create_person` and `update_person` call the shared `api.domain.person_names.prepare_person_name` for every name derivation. `update_person` merges `model_fields_set`-touched name parts against the person's stored parts (omitted stays, explicit `null`/blank clears) before calling `prepare_person_name` once on the merged result — atomic normalize+validate+derive, all four structured columns and `full_name` assigned together, or nothing assigned at all if the merged result is invalid. A successful authoritative name edit sets `person.name_needs_review = False` but never touches `name_extraction_metadata`. Deleted the old local `_derive_full_name` (no suffix comma, required both first AND last) entirely. `_missing_fields` and the `missing_filters` allow-list both gained a `"name review"` entry driven by `Person.name_needs_review`, reusing the existing People-directory pill/filter mechanism for either tab (D-12/D-13).
- `api/schemas/admin_jobs.py` / `api/services/admin_jobs.py`: `PersonCreate` mirrors the same structured-parts-only, `extra="forbid"` contract. `create_person_for_job` calls `prepare_person_name` before the job-existence/state check and the participant-scoping IDOR guard (pure validation, strictly more defensive, no guard weakened), then constructs the `Person` row with the derived parts/full_name. Every existing auth, job-state, participant-scope, and same-transaction linkage guard is unchanged.
- `api/routers/admin.py`: updated the two stale docstrings (`create_person`, `update_person`) that described the old `full_name`-accepting contract.
- Regression fixes in DB-gated tests that previously posted a client `full_name` (now-rejected): `test_admin_people.py`'s CR-01 test, `test_admin_jobs_phase25.py`'s five `PersonCreate(...)` call sites, and `test_isolation_survives_inner_commit.py`'s Phase 31 durability test — all switched to structured parts with equivalent assertions.

## Task Commits

Each task was committed atomically:

1. **Task 1: Enforce authority in people schemas and services** - `39c91c69` (feat)
2. **Task 2: Convert job mini-create without weakening guards** - `c05b280b` (feat)

## Files Created/Modified

- `api/schemas/admin_people.py` — `PersonUpdate`/`PersonCreateRequest` allow-list + `extra="forbid"`; new `NameExtractionMetadata`; `PersonDetail`/`PersonListItem` review/provenance fields
- `api/services/admin_people.py` — `create_person`/`update_person` route through `prepare_person_name`; `_missing_fields`/`missing_filters` "name review"; `_derive_full_name` removed
- `api/schemas/admin_jobs.py` — `PersonCreate` structured parts + `extra="forbid"`
- `api/services/admin_jobs.py` — `create_person_for_job` routes through `prepare_person_name`
- `api/routers/admin.py` — docstring updates on `create_person`/`update_person` routes
- `api/tests/test_admin_people_schemas_service.py` — allow-list/mass-assignment/first-only/last-only/"name review" unit tests; removed stale `_derive_full_name` tests
- `api/tests/test_admin_people.py` — full_name-rejection, partial-PATCH-merge, explicit-clear, missing-first-and-last, and name-review-clearing integration tests (real DB)
- `api/tests/test_admin_jobs_phase25.py` — `PersonCreate` schema/behavioral coverage updated for the structured-parts contract
- `api/tests/test_isolation_survives_inner_commit.py` — updated `PersonCreate` construction for the new contract

## Decisions Made

See `key-decisions` in frontmatter. In summary: `full_name` is removed as a field (not just made non-required) on every writable schema, backed by `extra="forbid"`, so a client attempt to author it is a hard validation error; the old buggy local formatter is deleted rather than kept as dead code since every write path now shares one helper; "name review" reuses the existing People-directory missing-field pill/filter pattern rather than introducing new UI surface; job mini-create validates the name before any job/participant lookup since that validation is pure and cannot weaken the existing IDOR guard; and job mini-create's provenance-prefill story is explicitly deferred to Plan 04, since a job-scoped create has no extraction source independent of the operator's own input at this layer.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed pre-existing DB-gated tests broken by the new mass-assignment contract**
- **Found during:** Task 1/Task 2 full-suite regression verification
- **Issue:** `test_admin_people.py`'s CR-01 regression test, all five `PersonCreate(...)` call sites in `test_admin_jobs_phase25.py`, and `test_isolation_survives_inner_commit.py`'s durability test posted a client-supplied `full_name` — now a 422 `ValidationError` under the new `extra="forbid"` contract. None of these three files are in this plan's `files_modified`, but all three are exercised by the plan's own `<verify>` commands (Task 1 explicitly runs `test_admin_people.py`; Task 2's DB-gated behavior depends on `test_admin_jobs_phase25.py`/is exercised in the same full-suite regression pass) and would otherwise fail for a reason unrelated to their own test intent.
- **Fix:** Replaced each `full_name="..."` construction with equivalent `first_name`/`last_name` structured parts and, where the test asserted on the created record, added a `full_name` assertion for the derived value — preserving each test's original intent (bench/advocate participant linkage, IDOR scoping, durability-across-sessions) unchanged.
- **Files modified:** `api/tests/test_admin_people.py`, `api/tests/test_admin_jobs_phase25.py`, `api/tests/test_isolation_survives_inner_commit.py`
- **Verification:** Full `api/tests` suite (403 tests) and `pipeline/tests` suite (152 passed, 5 xfailed) both green after the fix.
- **Committed in:** `39c91c69` (test_admin_people.py), `c05b280b` (test_admin_jobs_phase25.py, test_isolation_survives_inner_commit.py)

**2. [Rule 1 - Bug] Fixed a self-introduced CRLF line-ending regression in test_admin_jobs_phase25.py**
- **Found during:** Task 2, reviewing the diff before committing
- **Issue:** Editing `test_admin_jobs_phase25.py` via the Edit tool round-tripped the entire file's line endings from LF to CRLF, producing a ~2,000-line diff for what was actually a handful of real content changes (same class of regression documented in Plan 05's summary).
- **Fix:** Normalized the file back to LF via a direct byte-level `\r\n` → `\n` replace and re-verified `git diff --stat` showed only the real content change (68 lines) and the full test suite still passed unchanged (403 passed).
- **Files modified:** `api/tests/test_admin_jobs_phase25.py`
- **Verification:** `git diff --stat` reduced from 2,052 to 68 changed lines; `api/tests` suite unchanged at 403 passed.
- **Committed in:** `c05b280b`

---

**Total deviations:** 2 auto-fixed (both Rule 1 — necessary to keep the existing test suite green and to correct a self-introduced whitespace regression; neither expands scope beyond what this plan's own contract change required)
**Impact on plan:** No scope creep — both fixes were required side effects of Task 1/2's own schema change, not independent feature work.

## Issues Encountered

- **No reachable PostgreSQL in this execution environment** (same class of gap documented in Plan 02's summary). Provisioned an ephemeral, throwaway PostgreSQL 16 instance via the `pgserver` PyPI package (Unix-domain-socket-only, `cleanup_mode=None` so the server process persists across separate `alembic`/`pytest` subprocess invocations within this session), created a `scotus_test` database on it, and ran `alembic upgrade head` (migrations 0001–0022) cleanly before writing any test-verification code. Ran the full `api/tests` (403 passed) and `pipeline/tests` (152 passed, 5 xfailed) suites against it for regression safety — an ephemeral, session-only instance, torn down implicitly at session end, never connected to the project's real dev/CI database.
- **Full-suite `DATABASE_URL` pollution from an unrelated, pre-existing environmental interaction**: running the complete `api/tests` directory (not just this plan's target files) initially showed 13 unrelated failures with `ConnectionRefusedError` to `127.0.0.1:5432`. Root-caused to `test_migration_0022_person_name_authority.py` (Plan 02's own file, untouched by this plan) resolving `TEST_DATABASE_URL` from the project's real `.env` file — via `load_dotenv()`'s default `override=False` behavior populating an *unset* `TEST_DATABASE_URL` from `.env` — and then overwriting the process's `DATABASE_URL` with that real (unreachable-from-this-sandbox) value, breaking every DB-gated test collected afterward in the same session. This reproduces identically with zero changes to this plan's files (confirmed via `--ignore=api/tests/test_migration_0022_person_name_authority.py`, which alone restored 396/396 passing) and is a pre-existing, environment-specific hazard, not a regression introduced here. Worked around for verification purposes only by also exporting `TEST_DATABASE_URL` to my own ephemeral `scotus_test` connection string before the env var got a chance to be populated from `.env` — no project file, `.env`, or fixture was modified to work around this.

## User Setup Required

None — no external service configuration required. The ephemeral PostgreSQL instance used to verify this plan was session-only tooling; it is not part of the repository or any persisted environment.

## Next Phase Readiness

- `api/domain/person_names.prepare_person_name` is now the single write-path authority across the standalone people-directory create/update flow and the job-scoped mini-create — Plan 04 (pipeline/import/seed paths) can adopt the same helper with an established, tested pattern to follow (merge-then-validate for partial edits; validate-then-construct for fresh creates).
- The "name review" People-directory filter/indicator (`_missing_fields`/`missing_filters`) is live at the service layer and ready for Plan 06's frontend to surface as a click-to-filter pill, following the exact same vocabulary/mechanism as every other missing-field pill.
- `NameExtractionMetadata`/`name_needs_review` are now present on `PersonDetail`/`PersonListItem` API responses, ready for Plan 06's editor UI to render the stacked extracted-value hint (Plan 05's `CopyableExtractedValue` component already supports the needed `confidence`/`raw` props).
- Job mini-create's provenance-prefill story (D-14–D-18) is intentionally left to Plan 04's pipeline/import extraction paths, which are the actual source of extracted (non-operator-authored) name data; no blocker for that plan.
- No blockers. All 403 `api/tests` and 152 (+5 xfailed) `pipeline/tests` pass unchanged from the pre-plan baseline.

---
*Phase: 38-full-name-vs-name-parts-rethink*
*Completed: 2026-07-27*

## Self-Check: PASSED

- FOUND: api/schemas/admin_people.py
- FOUND: api/services/admin_people.py
- FOUND: api/schemas/admin_jobs.py
- FOUND: api/services/admin_jobs.py
- FOUND: api/routers/admin.py
- FOUND: api/tests/test_admin_people_schemas_service.py
- FOUND: api/tests/test_admin_people.py
- FOUND: api/tests/test_admin_jobs_phase25.py
- FOUND: api/tests/test_isolation_survives_inner_commit.py
- FOUND commit: 39c91c69 (Task 1)
- FOUND commit: c05b280b (Task 2)
