---
phase: 39-bench-popover-additional-context-data
plan: 01
subsystem: api
tags: [alembic, sqlalchemy, fastapi, pydantic, sveltekit, postgres]

# Dependency graph
requires:
  - phase: 37-tenure-seat-as-chief-associate-toggle
    provides: "The CheckConstraint + canonical-value + display-title-helper pattern (OFFICE_CHIEF/OFFICE_ASSOCIATE/office_title()) this plan mirrors for reason_left"
provides:
  - "alembic migrations 0023 (people.death_date) and 0024 (court_tenures.reason_left + ck_court_tenures_reason_left CHECK constraint)"
  - "api/models/models.py: REASON_RETIRED/REASON_DIED/REASON_PROMOTED, VALID_REASONS_LEFT, REASON_LEFT_TITLES, reason_left_title(), CourtTenure.reason_left, Person.death_date"
  - "api/schemas/speakers.py: TenureEntry.reason_left (raw canonical value)"
  - "api/services/speakers.py: reason_left wired into the per-tenure dict in Step 3a"
  - "SpeakerPopover.svelte: renders one reason line per tenure via a mirrored REASON_LEFT_TITLES/reasonLeftTitle() map"
affects: [39-02, 39-03, 39-04, 39-05, 39-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "reason_left-specific constant naming (VALID_REASONS_LEFT/REASON_LEFT_TITLES/reason_left_title()) mirrors Phase 37's office_title() pattern exactly, avoiding a generic REASON_*/VALID_REASONS name"
    - "Permanently-nullable CHECK constraint written as 'col IS NULL OR col IN (...)' — no matching alter_column(nullable=False) step, unlike the office pattern which pairs a CHECK constraint with a NOT NULL flip"

key-files:
  created:
    - alembic/versions/0023_add_person_death_date.py
    - alembic/versions/0024_add_constrain_tenure_reason_left.py
    - api/tests/test_tenure_reason_left.py
  modified:
    - api/models/models.py
    - api/schemas/speakers.py
    - api/services/speakers.py
    - app/src/lib/components/SpeakerPopover.svelte
    - "app/src/routes/cases/[slug]/arguments/[id]/+page.svelte"
    - api/tests/test_speakers_service.py
    - api/tests/test_migration_0022_person_name_authority.py

key-decisions:
  - "Both migrations (0023, 0024) were bundled into Task 1's commit rather than split strictly along the plan's Task 1/Task 2 file-list boundary, because 0024's down_revision chains through 0023 — the alembic head is only buildable with both files present. Person.death_date's ORM mapping itself still landed in Task 2's commit."
  - "Migrations applied only to a throwaway ephemeral pgserver-provisioned PostgreSQL instance in this WSL session, never to the real dev DB — real-DB application remains Plan 39-06's operator-run job per the plan's own environment note."

requirements-completed: [PUB-04]

coverage:
  - id: D1
    description: "A CourtTenure row storing reason_left='died' surfaces as reason_left: \"died\" inside that tenure's entry of GET /arguments/{id}/speakers"
    requirement: "PUB-04"
    verification:
      - kind: integration
        ref: "api/tests/test_speakers_service.py::TestGetArgumentSpeakersReasonLeft::test_tenure_reason_left_reaches_public_service_output"
        status: pass
    human_judgment: false
  - id: D2
    description: "reason_left_title() returns exactly 'Retired'/'Died in office'/'Promoted' for the three canonical values and raises KeyError for anything else"
    requirement: "PUB-04"
    verification:
      - kind: unit
        ref: "api/tests/test_tenure_reason_left.py::TestReasonLeftTitleExhaustiveness"
        status: pass
      - kind: unit
        ref: "api/tests/test_tenure_reason_left.py::TestValidReasonsLeftExhaustiveness"
        status: pass
    human_judgment: false
  - id: D3
    description: "court_tenures.reason_left CHECK constraint rejects an out-of-vocabulary value and accepts NULL; people.death_date is a nullable DATE column"
    requirement: "PUB-04"
    verification:
      - kind: integration
        ref: "manual asyncpg probe against ephemeral DB: NULL insert succeeds, 'resigned' insert raises IntegrityError"
        status: pass
      - kind: unit
        ref: "api/tests/test_tenure_reason_left.py::TestPersonDeathDate"
        status: pass
    human_judgment: false
  - id: D4
    description: "The bench popover renders one reason line per tenure that has a stored reason (no line when reason_left is null), with no per-value branching in the component"
    requirement: "PUB-04"
    verification:
      - kind: other
        ref: "cd app && npm run check — 0 errors (32 pre-existing warnings unchanged)"
        status: pass
      - kind: other
        ref: "! grep -Eq \"reason_left ===\" app/src/lib/components/SpeakerPopover.svelte"
        status: pass
    human_judgment: false

duration: ~70min
completed: 2026-07-28
status: complete
---

# Phase 39 Plan 01: Reason-left tracer slice Summary

**One column (`court_tenures.reason_left`) wired end to end — migration through ORM, canonical constants + display-title helper, public schema, service assembly, and popover render — plus `people.death_date`'s DB column and ORM mapping, both proven by a real DB-backed test of `get_argument_speakers()`.**

## Performance

- **Duration:** ~70 min (includes provisioning a throwaway ephemeral PostgreSQL instance for this WSL session — see Issues Encountered)
- **Completed:** 2026-07-28T15:08:15Z
- **Tasks:** 2 completed
- **Files modified:** 9 (2 new migrations, 1 new test module, 6 modified)

## Accomplishments
- `court_tenures.reason_left` (nullable VARCHAR(50)) + `ck_court_tenures_reason_left` CHECK constraint, constrained to exactly `retired`/`died`/`promoted`, permanently nullable (D-01/D-02) — verified the DB actually rejects `'resigned'` and accepts `NULL`.
- `people.death_date` (nullable DATE) — the second column migration 0016 explicitly deferred to this phase.
- `REASON_RETIRED`/`REASON_DIED`/`REASON_PROMOTED`/`VALID_REASONS_LEFT`/`REASON_LEFT_TITLES`/`reason_left_title()` in `api/models/models.py`, mirroring the Phase 37 `office_title()` shape exactly (D-15).
- `TenureEntry.reason_left` on the public schema; `api/services/speakers.py` Step 3a now includes `t.reason_left` per tenure — nothing else in that file's assembly logic touched.
- `SpeakerPopover.svelte` renders one reason line per tenure (13px/400/`#94a3b8`, identical treatment to every other metadata line) via a mirrored `REASON_LEFT_TITLES`/`reasonLeftTitle()` map that degrades to `''` for a non-canonical value — no per-value branching exists in the component.
- New DB-gated end-to-end test (`test_speakers_service.py`) seeding a `Person`/`Role`/`Argument`/`CourtTenure(office='associate', reason_left='died')`/`ArgumentParticipant(side=BENCH)`/`Utterance` and asserting `get_argument_speakers()`'s output carries `tenure[0]["reason_left"] == "died"`.
- New pure-Python test module (`test_tenure_reason_left.py`) pinning `reason_left_title()`'s exhaustiveness contract — 3 KeyError cases (unrecognized value, empty string, wrong case) plus a set-equality assertion between `VALID_REASONS_LEFT` and `REASON_LEFT_TITLES.keys()` — a direct test `office_title()` never got.

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end "why this tenure ended" — one column through every layer** - `7955702c` (feat) — bundles migrations 0023+0024 for alembic-chain buildability, plus the `reason_left`-side model/schema/service/frontend/test changes and the Rule-1 test-fixture bugfix below.
2. **Task 2: Add people.death_date and pin the display-title contract with a direct test** - `3e6de7a3` (test) — `Person.death_date` ORM mapping + `test_tenure_reason_left.py`.

No separate plan-metadata commit was made prior to this SUMMARY; the final `docs(39-01): complete reason-left tracer plan` commit follows this file.

## Files Created/Modified
- `alembic/versions/0023_add_person_death_date.py` - `people.death_date` nullable DATE column, pure add, no backfill
- `alembic/versions/0024_add_constrain_tenure_reason_left.py` - `court_tenures.reason_left` + `ck_court_tenures_reason_left` CHECK constraint (permanently nullable)
- `api/models/models.py` - `REASON_*`/`VALID_REASONS_LEFT`/`REASON_LEFT_TITLES`/`reason_left_title()`, `CourtTenure.reason_left`, `Person.death_date`
- `api/schemas/speakers.py` - `TenureEntry.reason_left`
- `api/services/speakers.py` - `str_tenures_by_person` dict now carries `reason_left`
- `app/src/lib/components/SpeakerPopover.svelte` - `TenureRow.reason_left`, `REASON_LEFT_TITLES`/`reasonLeftTitle()`, conditional reason `<p>` per tenure
- `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` - mirrored `TenureRow.reason_left` field on its own duplicate local interface (type-parity fix, see Deviations)
- `api/tests/test_speakers_service.py` - new `TestGetArgumentSpeakersReasonLeft` DB-gated tracer test
- `api/tests/test_tenure_reason_left.py` - new pure-Python exhaustiveness/contract test module
- `api/tests/test_migration_0022_person_name_authority.py` - `_leave_database_at_head` fixture bugfix (see Deviations)

## Decisions Made
- Bundled both migrations into Task 1's commit (see key-decisions above) rather than following the plan's literal file-per-task split, because `0024`'s `down_revision="0023"` makes the alembic chain unbuildable with only one file present — `Person.death_date`'s ORM mapping still landed in Task 2 as planned.
- Migrations were applied only to a throwaway ephemeral PostgreSQL instance provisioned for this session (via the `pgserver` PyPI package, per the plan's WSL/Windows split environment note) — never to the real dev database. **Plan 39-06 still needs to apply migrations 0023 and 0024 to the real dev DB as an operator step.**

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed `test_migration_0022_person_name_authority.py`'s `_leave_database_at_head` fixture hardcoding a stale revision instead of the real head**
- **Found during:** Task 1, full-suite verification (`pytest` with no args)
- **Issue:** The fixture's own docstring says it "restore[s] the shared test database to head once after every test in this module has finished," but its implementation ran `command.upgrade(cfg, TARGET_REVISION)` where `TARGET_REVISION = "0022"` — the head at the time Phase 38 wrote this test. Once this plan's migrations 0023/0024 became the real head, every alphabetically-later DB-gated test module in the same pytest session (e.g. `test_people.py`, `test_speakers_service.py`) started failing with `UndefinedColumnError: column "death_date" of relation "people" does not exist`, because the shared test DB was left at revision 0022 instead of the true head.
- **Fix:** Changed the restore step to `command.upgrade(cfg, "head")` (the literal Alembic head, resolved dynamically from the versions directory) instead of the hardcoded `TARGET_REVISION` constant. `TARGET_REVISION` itself is untouched and still correctly scopes the module's own test-target revision for its internal downgrade/upgrade cycles.
- **Files modified:** `api/tests/test_migration_0022_person_name_authority.py`
- **Verification:** Full suite (`pytest`, no args) went from 3 failures (`test_people.py` x2, `test_speakers_service.py` x1) to 740 passed / 5 xfailed / 0 failed after the fix. Re-ran `test_migration_0022_person_name_authority.py` in isolation and confirmed `alembic current` correctly reports `0024 (head)` after the module finishes.
- **Committed in:** `7955702c` (Task 1 commit)

**2. [Rule 3 - Blocking] Added `reason_left` to a second, duplicate `TenureRow` TypeScript interface**
- **Found during:** Task 1, `npm run check` verification
- **Issue:** `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` defines its own local `TenureRow`/`SpeakerDetail` interfaces (a pre-existing duplicate of `SpeakerPopover.svelte`'s own local types, not a shared module) to type the object it passes into `<SpeakerPopover speaker={...}>`. Adding `reason_left` to `SpeakerPopover.svelte`'s `TenureRow` without updating this second copy produced a `svelte-check` type error: "Property 'reason_left' is missing in type 'TenureRow' but required in type 'TenureRow'."
- **Fix:** Added the identical `reason_left: string | null` field (with a matching comment) to the `+page.svelte` copy of `TenureRow`.
- **Files modified:** `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte`
- **Verification:** `cd app && npm run check` — 0 errors (32 pre-existing warnings unchanged from baseline).
- **Committed in:** `7955702c` (Task 1 commit)

**3. [Rule 3 - Blocking] Repaired the local frontend dev environment's platform-specific optional dependencies**
- **Found during:** Task 1, `npm run check` verification
- **Issue:** `app/node_modules` was installed on the Windows side of this project's documented WSL/Windows split dev environment and had only Windows-platform native binaries (`@rollup/rollup-win32-x64-{gnu,msvc}`, `@esbuild/win32-x64`) — none for Linux, so `npm run check` failed immediately with `Cannot find module @rollup/rollup-linux-x64-gnu` when run from this WSL session (a known npm optional-dependency bug, npm/cli#4828).
- **Fix:** Installed the missing `@rollup/rollup-linux-x64-gnu@4.61.1` (exact version already pinned in `package-lock.json` as a declared optional dependency — not a new/unverified package) so `npm run check` could run at all in this session, then explicitly reinstalled the Windows-side binaries npm had removed as a side effect (`@rollup/rollup-win32-x64-gnu@4.61.1`, `@rollup/rollup-win32-x64-msvc@4.61.1`, `@esbuild/win32-x64@0.25.12`, all exact versions from `package-lock.json`) so the Windows side of the split dev environment is left exactly as it was found.
- **Files modified:** none tracked in git (`node_modules/` is gitignored; `package.json`/`package-lock.json` unchanged — `--no-save` used throughout).
- **Verification:** `npm run check` completed with 0 errors; `ls node_modules/@rollup/` and `ls node_modules/@esbuild/` confirmed both Linux and Windows binaries present afterward.
- **Committed in:** not committed (no tracked files changed).

---

**Total deviations:** 3 auto-fixed (1 bug, 2 blocking)
**Impact on plan:** All three were necessary to get the plan's own required verification commands (`pytest`, `npm run check`) to run and pass at all in this session. No scope creep — no other files were touched.

## Issues Encountered
- **No PostgreSQL reachable from this WSL sandbox, and no Windows-side Postgres accessible either** (the project's documented split-environment constraint). Provisioned a throwaway, session-local PostgreSQL 16 instance via the `pgserver` PyPI package (Unix-domain-socket only) in a scratch Python 3.12 venv (system Python was 3.14, which `pgserver` has no wheel for), created a `scotus_test` database on it, ran `alembic upgrade head` (through the new migrations 0023/0024) against it, and ran every automated verification command from this plan against it. Torn down and confirmed via `ps aux | grep postgres` at the end of the session — never connected to any real dev/CI database, no real data read or written.
- **`app/node_modules` only had Windows-platform optional binaries** — see Deviation 3 above.

## Next Phase Readiness
- The two migrations (0023, 0024), the `REASON_*` constants + `reason_left_title()` helper, and the `TenureEntry.reason_left`/`str_tenures_by_person["reason_left"]` wiring are all in place for Plans 39-02 through 39-05 to build on.
- **Plan 39-06 still needs to apply migrations 0023 and 0024 to the real dev database** — this plan only ran them against an ephemeral test instance, per the plan's own environment note.
- Full suite (`pytest`, no args): 740 passed, 5 xfailed, 0 failed against the ephemeral instance after this plan's changes.

## Self-Check: PASSED

All 10 created/modified source files and the SUMMARY itself confirmed present on disk; all 3 commits (`7955702c`, `3e6de7a3`, `8dc5ee93`) confirmed present in `git log --oneline --all`.

---
*Phase: 39-bench-popover-additional-context-data*
*Completed: 2026-07-28*
