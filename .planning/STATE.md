---
gsd_state_version: 1.0
milestone: v1.6
milestone_name: Backlog Cleanup
current_phase: 33
current_phase_name: `update_argument_metadata` unique-constraint guard
status: executing
stopped_at: Completed 40-01-PLAN.md
last_updated: "2026-07-14T13:01:29.124Z"
last_activity: 2026-07-13
last_activity_desc: Phase 32 complete, transitioned to Phase 33
progress:
  total_phases: 10
  completed_phases: 3
  total_plans: 16
  completed_plans: 14
  percent: 30
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-12 after v1.5 milestone completion)

**Core value:** Anyone can open a SCOTUS oral argument and immediately follow the conversation — the chat format makes speaker identity, turn-taking, and flow self-evident without legal background.
**Current focus:** Phase 32 — fix-courttenure-fk-bookkeeping-gap-in-merge-delete-person-se

## Current Position

Phase: 33 — `update_argument_metadata` unique-constraint guard
Plan: Not started
Status: Ready to execute
Last activity: 2026-07-13 — Phase 32 complete, transitioned to Phase 33

## Performance Metrics

v1.5: 10 phases, 55 plans, 10 days (2026-07-02 → 2026-07-12).

*Updated after each plan completion*

## Accumulated Context

### Decisions

Full decision log lives in PROJECT.md's Key Decisions table (all v1.0-v1.5 decisions logged there with outcomes). Cleared here at v1.5 milestone close per the standard STATE.md reset.

Two open design questions remain unresolved by design and are intentionally deferred to their own discuss-phase, not pre-decided in the roadmap:

- Phase 37 (Tenure Seat): numbered-seat data vs. binary Chief/Associate toggle
- Phase 38 (Full Name): auto-derive vs. independently editable
- [Phase 31]: _reset_test_db reads TEST_DATABASE_URL directly rather than depending on test_db_url/engine fixtures, avoiding fallback-to-shared-dev-DB risk (T-31-01)
- [Phase 31]: Database-name equality via sqlalchemy.engine.make_url used for all dev-DB/scotus_test guard checks instead of raw URL string comparison
- [Phase 31]: _REAL_DATABASE_URL captured before TEST_DATABASE_URL override so the leak-detection hooks always watch the real dev DB, never the redirected DATABASE_URL
- [Phase 31]: pytest_sessionstart/pytest_sessionfinish leak guard checks only people/arguments counts, not the full clean_db table list, to keep the failure message unambiguous
- [Phase 31]: Plan 03 canonical db_session fixture body taken from test_admin_jobs_list.py; docstring divergence across the 7 copies documented but non-blocking (functional code was byte-identical)
- [Phase 31]: [Phase 31, Plan 04]: Person duplicate survivor selection scores (court_tenures linkage, non-null bio field count, -id) as a tuple; lowest id is only the documented last-resort tie-break, never the default
- [Phase 31]: [Phase 31, Plan 04]: cleanup script deliberately excludes job-{id} source_docket values from orphan/pattern detection -- that is a legitimate production placeholder for in-progress admin-job arguments, not test leakage
- [Phase 31]: [Phase 31, Plan 04]: execute path re-runs detection inside the delete transaction and aborts if the candidate set drifted since the dry-run report, closing the TOCTOU gap between reporting and deleting
- [Phase 31, Plan 05]: Fixed 3 stale-identity-map bugs (publish_argument, unpublish_argument, approve_job) rather than xfailing them — db.refresh() after synchronize_session=False bulk updates, matching sibling functions
- [Phase 31, Plan 05]: api/core/config.py Settings needed a declared test_database_url field — pydantic-settings reads .env directly regardless of os.environ, independent of any conftest.py dotenv loading
- [Phase 31, Plan 05]: test_admin_jobs_phase25.py's committing-function tests (create_person_for_job, update_resolve_row_for_job) switched from the shared db_session fixture to per-block AsyncSessionLocal() sessions — commit() inside db_session's outer session.begin() breaks the transaction
- [Phase 31, Plan 06]: pytest.ini asyncio loop scope set to session (not conftest.py) to fix session-scoped engine fixture vs function-scoped event loop mismatch across pipeline/tests DB-gated tests
- [Phase 31, Plan 06]: SECTION_HINT_MAP plural regex bug (PETITIONERS/RESPONDENTS) fixed directly in state_machine.py rather than only documented -- self-contained, low-risk, real user-facing impact
- [Phase 31]: [Phase 31, Plan 07]: test_resolve_interrupt_sets_needs_review's full-suite-only failure root-caused to a module-reimport identity split (tests/test_admin_router.py reimports api.* mid-session; pipeline.commands.resolve keeps stale PipelineRun/PipelineRunStatus references) -- not the event-loop-policy theory in deferred-items.md, which bisection disproved
- [Phase 31]: [Phase 31, Plan 07]: test_argument_oyez_field.py/test_people.py's hardcoded id=1 assumption is permanently broken (pipeline/tests/test_seed_aliases.py's seeding tests are xfail stubs that never call run_seed_aliases()) -- fixed by making both tests self-contained rather than re-ordering fixtures
- [Phase 31]: Operator reviewed the 31-08 dry-run report and authorized the destructive cleanup; fresh re-detection immediately before --execute matched the authorized 81-row candidate set exactly, so no drift-abort was needed
- [Phase 32]: CourtTenure joins the blocking tier (Utterance/CaseAppearance/ArgumentParticipant), not the SpeakerAlias intrinsic-unconditional-delete tier (D-01)
- [Phase 32]: New field/key name is 'tenures' (matches existing tenure_coverage/tenure_gaps naming convention), not 'court_tenure'
- [Phase 32]: tenures joins the blocking tier (utterances/appearances/argument_participants) in the client-side can_delete/delete_block_count check, not the aliases bucket (D-01/D-05)
- [Phase 33]: Only concrete docket/question pairs participate in uniqueness checks — Matches PostgreSQL NULL uniqueness semantics
- [Phase 33]: Preserve submitted final pair structurally across rollback — Winner lookup must not use restored pre-update values
- [Phase 33]: Only validated duplicate_argument data with a positive integer conflict id crosses into form state — Prevents backend text and unsafe navigation ids from crossing the trust boundary
- [Phase 33]: Returned argued_date uses property presence for precedence — An attempted blank date is meaningful state and must override the loaded value
- [Phase 40]: Keep ADMIN_TOKEN duplicated across runtime env files with an explicit exact-match contract. — The API and SvelteKit server independently load the shared server-to-server credential.
- [Phase 40]: Keep all five SvelteKit variables server-private and group optional backend settings by operating concern. — This makes runtime ownership clear and avoids exposing credentials through public environment variables.

### Roadmap Evolution

v1.5's roadmap evolution (Phase 29 added, Phase 30.1 inserted) is archived in `.planning/milestones/v1.5-ROADMAP.md`. Cleared here at milestone close.

2026-07-13: Phases 31–40 moved from ROADMAP.md's "Unscheduled Phases" section into the active "## Phases" / "## Phase Details" sections for v1.6 — no renumbering, no new phases created; requirement coverage 11/11 confirmed.

### Pending Todos

- `2026-07-08-edit-affordance-on-utterances-and-speaker-popover.md` (ui) — authenticated "Edit" affordance on every utterance + on the speaker popover card; no phase assigned yet

### Blockers/Concerns

Deployment blockers (v1.4, unresolved — not in v1.6 scope):

- `BODY_SIZE_LIMIT=10M` must be set in DO App Platform env
- `ORIGIN`, `PROTOCOL_HEADER`, `HOST_HEADER` env vars required on DO
- `admin.scotuschat.com` DNS entry must be created before smoke test
- admin_arguments.py::delete_argument omits argument_status_log from its FK cascade (found during 31-04) -- likely ForeignKeyViolation on deleting a DRAFT argument with a status log row; see deferred-items.md for suggested fix

## Deferred Items

Items acknowledged and deferred at v1.5 milestone close on 2026-07-12:

| Category | Item | Status |
|----------|------|--------|
| todo | 2026-07-08-edit-affordance-on-utterances-and-speaker-popover.md | pending (ui, no phase assigned) |
| seed | SEED-001-rework-resolve-table-requirements | dormant |
| context_question | Phase 999.2 (999.2-CONTEXT.md, 3 open questions) | not started |

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| verification | 01-VERIFICATION.md | human_needed (stale — human UAT completed per commits) | 2026-06-15 |
| verification | 03-VERIFICATION.md | human_needed (stale — 03-HUMAN-UAT.md: complete) | 2026-06-15 |
| verification | 04-VERIFICATION.md | human_needed (stale — 04-UAT.md: passed) | 2026-06-15 |
| verification | 11-VERIFICATION.md | human_needed (v1.2 carry-over — Argument Metadata Editing human UAT not formally closed) | 2026-06-29 |
| Phase 22 P01 | 2 | 3 tasks | 3 files |
| Phase 22 P02 | 15m | 3 tasks | 7 files |
| Phase 23 P01 | 2m | 2 tasks | 4 files |
| Phase 23 P02 | 2 | 1 tasks | 1 files |
| Phase 23 P03 | 5m | 2 tasks | 2 files |
| Phase 23 P04 | 10m | 5 tasks | 4 files |
| Phase 23 P05 | 5m | 1 tasks | 1 files |
| Phase 23 P07 | 12 | 3 tasks | 6 files |
| Phase 24 P01 | 35m | 1 tasks | 3 files |
| Phase 24 P02 | 2min | 1 tasks | 1 files |
| Phase 24 P03 | 10min | 1 tasks | 1 files |
| Phase 24 P04 | 35m | 2 tasks | 9 files |
| Phase 24 P05 | 20m | 2 tasks | 4 files |
| Phase 25 P01 | 45min | 3 tasks | 5 files |
| Phase 25 P02 | 35min | 3 tasks | 4 files |
| Phase 25 P03 | 40min | 2 tasks | 2 files |
| Phase 25 P04 | 55min | 3 tasks | 5 files |
| Phase 26 P01 | 20min | 2 tasks | 6 files |
| Phase 26 P03 | 15min | 2 tasks | 2 files |
| Phase 26 P02 | 20min | 2 tasks | 5 files |
| Phase 26 P04 | 12min | - tasks | - files |
| Phase 26 P05 | 15min | 3 tasks | 4 files |
| Phase 26 P06 | 20min | 2 tasks | 4 files |
| Phase 27 P01 | 5min | 2 tasks | 3 files |
| Phase 27 P02 | 12min | 2 tasks | 2 files |
| Phase 27 P03 | 20min | 3 tasks | 3 files |
| Phase 27-people-admin P04 | 15min | 2 tasks | 2 files |
| Phase 27-people-admin P05 | 15min | 2 tasks | 2 files |
| Phase 27 P06 | 20min | 2 tasks | 2 files |
| Phase 27 P07 | 8min | 1 tasks | 1 files |
| Phase 27 P08 | 15min | 2 tasks | 4 files |
| Phase 27 P09 | 7min | 2 tasks | 3 files |
| Phase 27 P10 | 5min | 2 tasks | 1 files |
| Phase 27 P11 | 8min | 1 tasks | 1 files |
| Phase 29 P01 | 15min | 3 tasks | 6 files |
| Phase 29 P02 | 12min | 3 tasks | 7 files |
| Phase 29-historical-corpus-import P03 | 25min | 3 tasks | 3 files |
| Phase 29 P06 | 12min | 3 tasks | 8 files |
| Phase 29 P04 | 25min | 3 tasks | 3 files |
| Phase 29 P05 | 45min | 2 tasks | 3 files |
| Phase 29 P07 | 4min | 2 tasks | 5 files |
| Phase 29 P08 | 10min | 2 tasks | 3 files |
| Phase 29 P09 | 20min | 2 tasks | 2 files |
| Phase 30 P01 | 20min | 2 tasks | 3 files |
| Phase 30 P02 | 15min | 2 tasks | 3 files |
| Phase 30 P03 | 12min | 2 tasks | 1 files |
| Phase 30 P04 | N/A | 2 tasks | 0 files |
| Phase 28 P01 | 30min | 3 tasks | 5 files |
| Phase 28 P02 | 20min | 2 tasks | 2 files |
| Phase 28 P03 | 25min | 3 tasks | 3 files |
| Phase 30.1 P01 | 5min | 3 tasks | 5 files |
| Phase 30.1 P02 | 12min | 2 tasks | 2 files |
| Phase 30.1 P03 | 20min | 2 tasks | 6 files |
| Phase 31 P01 | 25min | 2 tasks | 3 files |
| Phase 31 P02 | 20min | 2 tasks | 1 files |
| Phase 31 P03 | 15min | 3 tasks | 8 files |
| Phase 31 P04 | 20min | 2 tasks | 1 files |
| Phase 31 P05 | 55min | 1 tasks | 9 files |
| Phase 31 P06 | 40min | 1 tasks | 6 files |
| Phase 31 P07 | 55min | 2 tasks | 5 files |
| Phase 31 P08 | 25min | 2 tasks | 1 files |
| Phase 32 P01 | 15min | 2 tasks | 3 files |
| Phase 32 P02 | 10min | 2 tasks | 2 files |
| Phase 33 P01 | 12min | 2 tasks | 5 files |
| Phase 33 P03 | 3min | 2 tasks | 4 files |
| Phase 40 P01 | 10m | 2 tasks | 3 files |

## Session Continuity

Last session: 2026-07-14T13:01:29.086Z
Stopped at: Completed 40-01-PLAN.md
Resume file: None

## Operator Next Steps

- Review the v1.6 roadmap; then run /gsd-discuss-phase 31 (or /gsd-plan-phase 31 if discussion is unnecessary for a well-scoped bug fix) to begin execution
