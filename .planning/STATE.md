---
gsd_state_version: 1.0
milestone: v1.6
milestone_name: Backlog Cleanup
current_phase: 38
current_phase_name: full-name-vs-name-parts-rethink
status: executing
stopped_at: Completed 38-05-PLAN.md
last_updated: "2026-07-22T16:19:51.451Z"
last_activity: 2026-07-22
last_activity_desc: Phase 38 execution started
progress:
  total_phases: 10
  completed_phases: 8
  total_plans: 38
  completed_plans: 34
  percent: 80
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-14 after Phase 34 verification)

**Core value:** Anyone can open a SCOTUS oral argument and immediately follow the conversation — the chat format makes speaker identity, turn-taking, and flow self-evident without legal background.
**Current focus:** Phase 38 — full-name-vs-name-parts-rethink

## Current Position

Phase: 38 (full-name-vs-name-parts-rethink) — EXECUTING
Plan: 3 of 6
Status: Ready to execute
Last activity: 2026-07-22 — Phase 38 execution started

## Performance Metrics

v1.5: 10 phases, 55 plans, 10 days (2026-07-02 → 2026-07-12).

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 37 P03 | 25min | 3 tasks | 7 files |
| Phase 37 P04 | 50min | 2 tasks | 8 files |
| Phase 37 P05 | 90min | 3 tasks | 6 files |
| Phase 38 P01 | 17min | 3 tasks | 4 files |
| Phase 38 P05 | 40min | 3 tasks | 6 files |

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
- [Phase 40]: Portable PostgreSQL uses dev-start.ps1 as a recurring-start command only; bootstrap prerequisites remain explicit. — The script starts, migrates, and launches but does not initialize dependencies, env files, or the cluster.
- [Phase 40]: Portable and Windows-service PostgreSQL share the scotus role/database contract and Alembic-only DDL path. — One DATABASE_URL contract keeps both first-class setup branches consistent.
- [Phase 34]: source_dockets is authoritative when supplied and its first normalized entry is canonical
- [Phase 34]: Required PATCH fields retain Optional defaults so omission remains distinct from explicit null
- [Phase 34]: Required action errors are identified only from terminal Pydantic detail loc fields
- [Phase 34]: Failure payloads preserve raw Case strings and metadata empty-array presence
- [Phase 34]: Native invalid events are suppressed and Case constraints accumulate before first-invalid focus
- [Phase 34]: Empty editable pill submissions are canceled client-side while readonly behavior is unchanged
- [Phase 34]: Clear only native-owned required flags at the constraint-valid enhanced-submit boundary; later server-required state remains authoritative
- [Phase ?]: [Phase 35, Plan 02]: Removal is represented by complete absence of the rerun action and error payload; no compatibility UI was added.
- [Phase 35]: Retire same-source recreation by deleting the route and service function, leaving ordinary creation and durable history unchanged.
- [Phase 35]: Retain broad rerun wording only where it describes legitimate PipelineRun history rather than an operator capability.
- [Phase 35]: Exact retired-symbol matches are allowed only in deliberate negative regressions; broad rerun language remains for legitimate run history and re-execution semantics.
- [Phase 35]: Commit-owning public-boundary tests use the configured isolated database with explicit cleanup.
- [Phase 36]: Phase 36 owns the click-to-copy interaction contract while Phase 38 may evolve its visual presentation.
- [Phase 36]: Disabled N/A values retain disabled semantics and tooltip behavior but omit the copy icon.
- [Phase 36]: Use extracted fills the native date input without autosave while preserving manual entry.
- [Phase 36]: Copy feedback ownership follows a generation invalidated by activation, payload change, and destruction. — Prevents stale clipboard promises and timers from mutating feedback for the current payload.
- [Phase 37]: Wave 0 tests fail at execution rather than collection when Phase 37 production artifacts are absent.
- [Phase 37]: Native same-name radio semantics are the executable accessibility baseline for Office selection.
- [Phase 37]: Execution consumes an immutable database-bound report as the sole audited row set. — Prevents report regeneration, tampering, and cross-database execution.
- [Phase 37]: The database constraint is installed only after a preflight proves every office canonical. — Keeps legacy values readable until explicit normalization is complete.
- [Phase ?]: [Phase 37]: CourtTenure.office declares its own named CheckConstraint (ck_court_tenures_office) mirroring migration 0021's DB constraint, purely for ORM self-documentation — Alembic remains sole DDL authority.
- [Phase ?]: [Phase 37]: TenureWrite (strict Literal office) and TenureRow (tolerant Optional office) are two separate schemas so writes can never accidentally reuse read-response tolerance (D-03/D-04 and D-11 coexist).
- [Phase ?]: [Phase 37]: _bench_role_and_missing_tenure returns office_title(t.office) (formal display title) rather than the raw chief/associate storage value.
- [Phase ?]: [Phase 37, Plan 04]: api/services/admin_arguments.py required zero source changes -- it never accesses CourtTenure.seat/office directly, only the already-converted _bench_role_and_missing_tenure() helper; only its DB fixture test needed office=.
- [Phase ?]: [Phase 37, Plan 04]: SpeakerPopover.svelte defines its own small exhaustive OFFICE_TITLES/officeTitle() map rather than a shared Python/TS module -- intentional duplication for a two-entry map, not a new cross-layer dependency.
- [Phase ?]: [Phase 37, Plan 04]: TenureEntry and both frontend TenureRow types carry the raw canonical office value end to end; only SpeakerPopover.svelte's officeTitle() projects to the formal display title at the final render boundary.
- [Phase ?]: [Phase 37-05] aria-invalid/aria-describedby placed on a nested role="radiogroup" div, not the fieldset (implicit "group" role) or individual radios ("radio" role) — the only role in this markup ARIA permits aria-invalid on
- [Phase ?]: [Phase 37-05] Submit-button onclick preventDefault() used as the client-side Office preflight gate instead of threading validation through use:enhance's cancel() callback
- [Phase ?]: [Phase 37-05] scripts/audit_tenure_seat_identifiers.py uses an exact (path,line,text) allowlist rather than fuzzy pattern exceptions, and fails on stale (no-longer-matching) allowlist entries too
- [Phase ?]: [Phase 38, Plan 01]: PersonNameError carries a stable .code attribute (at_least_one_required, length_exceeded, full_name_length_exceeded, invalid_confidence, provenance_value_length_exceeded, provenance_raw_length_exceeded) for deterministic branching instead of message-text matching
- [Phase ?]: [Phase 38, Plan 01]: split_legacy_full_name distinguishes Medium (round-trip near-miss, e.g. irregular whitespace) from Low (structurally ambiguous: single-part, particle, >3 tokens, inverted punctuation order, suffix without a leading comma); auto_apply is true only for High confidence
- [Phase ?]: [Phase 38, Plan 01]: A suffix token (Jr./Sr./II/III/IV) is only recognized as a suffix when it follows a comma -- the same literal without a comma is an order/punctuation ambiguity, never guessed
- [Phase ?]: [Phase 38, Plan 05]: Stacked provenance mode on CopyableExtractedValue activates only when a caller passes confidence and/or raw (even null) -- every existing value-only/pill consumer stays byte-for-byte unchanged
- [Phase ?]: [Phase 38, Plan 05]: Legacy metadata fields with no independently stored raw/confidence (title_hint, case_name, argued_date, primary_docket, question_number) use an explicit Medium confidence fallback and the field's own extracted text as raw at the Svelte call-site boundary, never a fabricated percentage
- [Phase ?]: [Phase 38, Plan 05]: DocketPillInput Docket Pill provenance states are additive -- only pills whose entry carries confidence/raw route through CopyableExtractedValue; all current plain-string callers (ArgumentDetailsCard.svelte, pipeline create-job page) keep exact legacy markup and remain untouched/out of scope for this plan

### Roadmap Evolution

v1.5's roadmap evolution (Phase 29 added, Phase 30.1 inserted) is archived in `.planning/milestones/v1.5-ROADMAP.md`. Cleared here at milestone close.

2026-07-13: Phases 31–40 moved from ROADMAP.md's "Unscheduled Phases" section into the active "## Phases" / "## Phase Details" sections for v1.6 — no renumbering, no new phases created; requirement coverage 11/11 confirmed.

- Phase 35 edited: edited fields: title, goal, depends_on, requirements, success_criteria

### Pending Todos

- `2026-07-08-edit-affordance-on-utterances-and-speaker-popover.md` (ui) — authenticated "Edit" affordance on every utterance + on the speaker popover card; no phase assigned yet

### Blockers/Concerns

Deployment blockers (v1.4, unresolved — not in v1.6 scope):

- `BODY_SIZE_LIMIT=10M` must be set in DO App Platform env
- `ORIGIN`, `PROTOCOL_HEADER`, `HOST_HEADER` env vars required on DO
- `admin.scotuschat.com` DNS entry must be created before smoke test
- admin_arguments.py::delete_argument omits argument_status_log from its FK cascade (found during 31-04) -- likely ForeignKeyViolation on deleting a DRAFT argument with a status log row; see deferred-items.md for suggested fix
- [Phase 38, Plan 05] Discovered pre-existing working-tree anomaly (not caused by this plan's commands): .planning/REQUIREMENTS.md and every .planning/phases/<NN>-* directory except 38-full-name-vs-name-parts-rethink/ are missing from disk (REQUIREMENTS.md and phase 31-40 tracked files show as git 'D'; untracked Phase 38 PLAN/RESEARCH/PATTERNS/UI-SPEC/FIGMA/VALIDATION files are gone with no git trace since they were never committed). This caused roadmap.update-plan-progress to report 'No plans found' (skipped, no ROADMAP.md changes made) and state.advance-plan/update-progress to zero out STATE.md's progress counters as a side effect (manually restored to the pre-corruption values: completed_phases 8, total_plans 38, completed_plans 34, percent 80, before committing). Needs investigation/recovery -- likely git checkout of tracked 'D' paths from HEAD for phases 31-40, and regeneration or recovery of untracked Phase 38 planning docs and REQUIREMENTS.md from another agent/session if available. Not remediated here: out of this plan's scope and risks colliding with concurrent wave agents (38-02/03/04) sharing this same non-worktree-isolated working tree.

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
| Phase 40 P02 | 2m | 3 tasks | 1 files |
| Phase 33 P04 | 4 min | 1 tasks | 3 files |
| Phase 34 P01 | 10m | 2 tasks | 4 files |
| Phase 34 P02 | 8m | 2 tasks | 3 files |
| Phase 34 P03 | 10m | 2 tasks | 4 files |
| Phase 34 P04 | 35min | 1 tasks | 3 files |
| Phase 35 P02 | 10min | 2 tasks | 2 files |
| Phase 35 P01 | 12min | 2 tasks | 3 files |
| Phase 35 P03 | 20min | 2 tasks | 2 files |
| Phase 36 P01 | 16min | 2 tasks | 2 files |
| Phase 36 P02 | 2h | 3 tasks | 6 files |
| Phase 36 P03 | 18m | 2 tasks | 5 files |
| Phase 37 P01 | 20min | 2 tasks | 2 files |
| Phase 37 P02 | 18min | 3 tasks | 3 files |

## Session Continuity

Last session: 2026-07-22T16:16:15.864Z
Stopped at: Completed 38-05-PLAN.md
Resume file: None

## Operator Next Steps

- Run $gsd-verify-work 35 to validate the completed capability removal, or continue the already-prepared Phase 37 design work.
