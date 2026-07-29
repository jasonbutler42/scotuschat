---
gsd_state_version: 1.0
milestone: v1.6
milestone_name: Backlog Cleanup
current_phase: 39
current_phase_name: bench-popover-additional-context-data
status: executing
stopped_at: Completed 39-08-PLAN.md (bench popover mockup-fidelity gap closure)
last_updated: "2026-07-29T01:29:18.085Z"
last_activity: 2026-07-28
last_activity_desc: Phase 39 execution started
progress:
  total_phases: 10
  completed_phases: 9
  total_plans: 51
  completed_plans: 50
  percent: 90
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-14 after Phase 34 verification)

**Core value:** Anyone can open a SCOTUS oral argument and immediately follow the conversation — the chat format makes speaker identity, turn-taking, and flow self-evident without legal background.
**Current focus:** Phase 39 — bench-popover-additional-context-data

## Current Position

Phase: 39 (bench-popover-additional-context-data) — EXECUTING
Plan: 3 of 9
Status: Ready to execute
Last activity: 2026-07-28 — Phase 39 execution started

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
| Phase 38 P02 | 65min | 2 tasks | 3 files |
| Phase 38 P03 | ~70min | 2 tasks | 9 files |
| Phase 38 P04 | ~50min | 3 tasks | 6 files |
| Phase 38 P06 | ~50min | 3 tasks | 8 files |
| Phase 38 P07 | 20min | 2 tasks | 5 files |
| Phase 38 P08 | 20min | 2 tasks | 2 files |
| Phase 38 P09 | 20min | 3 tasks | 5 files |
| Phase 38 P10 | ~15min | 2 tasks | 1 files |
| Phase 39 P01 | ~70min | 2 tasks | 10 files |
| Phase 39 P02 | ~55min | 2 tasks | 2 files |
| Phase 39 P03 | ~40min | 2 tasks | 5 files |
| Phase 39 P04 | ~2h | 2 tasks | 4 files |
| Phase 39 P05 | ~30min | 2 tasks | 2 files |
| Phase 39 P07 | ~50min | 2 tasks | 4 files |
| Phase 39 P08 | 35min | 2 tasks | 2 files |

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
- [Phase ?]: [Phase 38, Plan 02]: Migration 0022 only examines Person rows where first_name/middle_name/last_name/name_suffix are ALL NULL -- any row already carrying a structured part is left completely untouched (never split, never flagged for review)
- [Phase ?]: [Phase 38, Plan 02]: name_extraction_metadata is written for every examined legacy row (applied and reviewed alike) as {source, raw, confidence, reason, auto_applied}, validated through prepare_name_provenance, giving reviewed rows a durable audit trail for the future Name review surface
- [Phase ?]: [Phase 38, Plan 02]: A blank/whitespace-only full_name aborts the entire migration 0022 transaction (Postgres transactional DDL rolls back schema+data together) rather than being silently skipped or guessed
- [Phase ?]: [Phase 38, Plan 02]: Downgrade drops only name_extraction_metadata then name_needs_review (reverse of add order) and never rewrites full_name or structured columns for applied or reviewed rows
- [Phase ?]: [Phase 38, Plan 03]: PersonUpdate/PersonCreateRequest/admin_jobs.PersonCreate drop full_name entirely (extra="forbid") -- a client-supplied full_name is a 422, not a silently-ignored write
- [Phase ?]: [Phase 38, Plan 03]: update_person merges model_fields_set-touched name parts against stored state before one prepare_person_name call -- atomic normalize+validate+derive, omitted vs explicitly-cleared parts distinguished
- [Phase ?]: [Phase 38, Plan 03]: An authoritative name edit clears Person.name_needs_review but never touches name_extraction_metadata -- independent, permanent audit trail (D-15)
- [Phase ?]: [Phase 38, Plan 03]: "name review" reuses the existing People-directory missing-field pill/filter mechanism rather than new UI (D-12/D-13), applying to both Bench and Advocate tabs
- [Phase ?]: [Phase 38, Plan 04]: import_justices_csv.py's blank-only prefill is per-field (CSV columns are independent per-part ground truth); import_convokit.py's blank-only prefill is whole-row, mirroring migration 0022's guard exactly (a derived split's parts are not independently trustworthy the way CSV columns are)
- [Phase ?]: [Phase 38, Plan 04]: import_convokit.py's provenance raw/confidence is derived from the Person row's own stored full_name, not the corpus label passed into that call -- matters for the oyez_speaker_id-matched path where the corpus label can legitimately differ from what's saved
- [Phase ?]: [Phase 38, Plan 06]: personNames.ts is a preview-only display mirror with no persistence path -- Node v22.6+/v23.6+ executes it directly for genuine cross-language parity verification against the shared fixture, no ts-node/vitest needed
- [Phase ?]: [Phase 38, Plan 06]: Per-part extracted-value hints (First/Middle/Last/Suffix) each render independently but share one whole-record name_extraction_metadata envelope -- an unfilled ambiguous field shows the Phase 36 disabled N/A + shared raw/confidence with no extra component logic
- [Phase ?]: [Phase 38, Plan 06]: 'Name review' reuses the existing click-to-filter pill mechanism verbatim via a pillLabel() display-text helper -- the underlying filter vocabulary stays lowercase (matches the API's missing_filters allow-list); only the visible/accessible text is Title Case
- [Phase ?]: [Phase 38, Plan 07]: Character allow-list (^[A-Za-z0-9][A-Za-z0-9_-]*$) plus a 64-char cap chosen over a strict SCOTUS docket-shape regex for normalize_docket_value -- a strict shape regex would reject real accepted shapes (bare numbers, ConvoKit historical shapes, synthetic job-{id} dockets, existing data/pdfs/ files)
- [Phase ?]: [Phase 38, Plan 07]: normalize_docket_value's check ordering (blank, then length, then pattern) is a hard determinism contract -- the 68-char UAT-reported quoted string resolves to length_exceeded, not invalid_characters, because length is checked first
- [Phase ?]: [Phase 38, Plan 07]: T-24-08's leading-hyphen argv guard in _normalize_dockets stays unmodified and runs before the new normalize_docket_value check; the domain rule is additive, not a replacement, even though it independently subsumes the same input class
- [Phase ?]: [Phase 38, Plan 08]: Used pathlib.PurePath (not the module's Path, which existing DB-dependent tests patch to a mock) for the docket guard's structural is_absolute/parts check, keeping the guard's I/O-free path parsing decoupled from the mocked Path used for file writes
- [Phase ?]: [Phase 38, Plan 08]: The docket guard runs uniformly on every docket in all_dockets, including the synthetic job-{id} docket, with no special-case exemption
- [Phase ?]: [Phase 38, Plan 09]: Docket TS/Python parity locked via source extraction + Python execution of the extracted rule, not a node subprocess -- avoids the known-broken Windows-path node driver pattern in test_phase38_people_ui_contract.py
- [Phase ?]: [Phase 38, Plan 09]: enforceShape on DocketPillInput defaults to false and is opt-in only for the Pipeline Runner's New Run form; ArgumentDetailsCard.svelte stays untouched (contract-tested at 0 references) since its API contract has no equivalent path-hazard constraint
- [Phase ?]: [Phase 38, Plan 09]: On a shape-error rejection, DocketPillInput preserves the attempted input value and does not add a pill; the SvelteKit action's docket-error fail(400) never echoes the value or forwards FastAPI's 422 detail verbatim (T-07-13 posture retained)
- [Phase ?]: [Phase 38, Plan 10]: G-38-6 closed only after both the automated regression gate and explicit operator re-verification of all 6 checkpoint steps on the live Pipeline Runner, matching the plan's premise that a UI-found gap is closed by a human at the UI
- [Phase ?]: [Phase 38, Plan 10]: 38-UAT.md's pre-existing test_phase38_people_ui_contract.py node-driver failure was left undisturbed and only noted, per plan scope
- [Phase ?]: [Phase 39, Plan 01]: Bundled migrations 0023+0024 into Task 1's commit (rather than the plan's literal Task 1/Task 2 file split) because 0024's down_revision chains through 0023 -- alembic head is only buildable with both present; Person.death_date's ORM mapping still landed in Task 2
- [Phase ?]: [Phase 39, Plan 01]: Migrations applied only to an ephemeral pgserver-provisioned PostgreSQL instance this session, never the real dev DB -- Plan 39-06 must still apply 0023/0024 to the real dev DB as an operator step
- [Phase ?]: [Phase 39, Plan 02]: Membership check (value in map), not .get(), used to resolve CSV Reason Left -- keeps a recognised value that maps to None ('Still in Office') distinguishable from a never-seen value, which increments a reasons_unmatched counter instead
- [Phase ?]: [Phase 39, Plan 02]: Accidentally applied migrations 0023/0024 to the real dev DB via the Windows .venv (WSL interop does not forward shell env vars into the Windows subprocess) -- additive-only, non-destructive, and functionally completes part of Plan 39-06's job early; all actual test execution for this plan used a separate ephemeral WSL pgserver instance
- [Phase ?]: [Phase 39, Plan 03]: death_date write in update_person guarded by model_fields_set (not is not None), placed in the birthdate/save-form guard group -- mirrors the Pitfall 5 regression guard pinned by a named test
- [Phase ?]: [Phase 39, Plan 04]: appointing_president_party exposed on the public speaker popover payload, reversing T-14-02; top-level appointing_president retired in favour of per-tenure appointed_by (D-11/D-12/D-13) -- promote not add-alongside
- [Phase ?]: [Phase 39, Plan 05]: Bio-toggle visibility uses scrollHeight/clientHeight measurement (39-UI-SPEC.md's primary option), not the character-length threshold fallback
- [Phase ?]: [Phase 39, Plan 05]: .popover-card container changed to display:block rather than flex-column since every stacked section already carries its own margin-top
- [Phase ?]: [Phase 39, Plan 07]: Split combined two-task edit into two atomic per-task commits by temporarily reverting Task 2's additions, verifying/committing Task 1 alone, then reapplying Task 2 -- preserves per-task traceability
- [Phase ?]: [Phase 39, Plan 07]: Presence-guarded conditional spread (...(bioTextSubmitted ? { bio_text } : {})) used for bio_text instead of an unconditional property like birthdate/death_date -- protects against a future caller posting to save-form without the Biography card in the DOM
- [Phase ?]: [Phase 39, Plan 08]: Wrote the popover UI-contract test module before touching the component (TDD RED first), confirming the RED run failed exactly the 10 tests predicted by the plan's acceptance criteria
- [Phase ?]: [Phase 39, Plan 08]: Bundled the president/party {@render separator(4)} replacement into Task 1's commit rather than Task 2's, since Task 1's action text calls for replacing both inline separators through the snippet
- [Phase ?]: [Phase 39, Plan 08]: Used a brace-balanced _function_body() extraction in the test module to check formatMonthYear's body specifically for absence of day:, avoiding a false-fail against formatShort's own legitimate day: 'numeric'

### Roadmap Evolution

v1.5's roadmap evolution (Phase 29 added, Phase 30.1 inserted) is archived in `.planning/milestones/v1.5-ROADMAP.md`. Cleared here at milestone close.

2026-07-13: Phases 31–40 moved from ROADMAP.md's "Unscheduled Phases" section into the active "## Phases" / "## Phase Details" sections for v1.6 — no renumbering, no new phases created; requirement coverage 11/11 confirmed.

- Phase 35 edited: edited fields: title, goal, depends_on, requirements, success_criteria

### Pending Todos

- `2026-07-08-edit-affordance-on-utterances-and-speaker-popover.md` (ui) — authenticated "Edit" affordance on every utterance + on the speaker popover card; no phase assigned yet
- `2026-07-28-unpublished-argument-visible-in-cases-list.md` (bug) — unpublished argument still shows in `/cases/` list and is directly accessible by URL; found during Phase 39's 39-06 checkpoint, unrelated to that phase's scope

### Blockers/Concerns

Deployment blockers (v1.4, unresolved — not in v1.6 scope):

- `BODY_SIZE_LIMIT=10M` must be set in DO App Platform env
- `ORIGIN`, `PROTOCOL_HEADER`, `HOST_HEADER` env vars required on DO
- `admin.scotuschat.com` DNS entry must be created before smoke test
- admin_arguments.py::delete_argument omits argument_status_log from its FK cascade (found during 31-04) -- likely ForeignKeyViolation on deleting a DRAFT argument with a status log row; see deferred-items.md for suggested fix
- [Phase 38, Plan 05] Discovered pre-existing working-tree anomaly (not caused by this plan's commands): .planning/REQUIREMENTS.md and every .planning/phases/<NN>-* directory except 38-full-name-vs-name-parts-rethink/ are missing from disk (REQUIREMENTS.md and phase 31-40 tracked files show as git 'D'; untracked Phase 38 PLAN/RESEARCH/PATTERNS/UI-SPEC/FIGMA/VALIDATION files are gone with no git trace since they were never committed). This caused roadmap.update-plan-progress to report 'No plans found' (skipped, no ROADMAP.md changes made) and state.advance-plan/update-progress to zero out STATE.md's progress counters as a side effect (manually restored to the pre-corruption values: completed_phases 8, total_plans 38, completed_plans 34, percent 80, before committing). Needs investigation/recovery -- likely git checkout of tracked 'D' paths from HEAD for phases 31-40, and regeneration or recovery of untracked Phase 38 planning docs and REQUIREMENTS.md from another agent/session if available. Not remediated here: out of this plan's scope and risks colliding with concurrent wave agents (38-02/03/04) sharing this same non-worktree-isolated working tree.
- [Phase 39, Plan 02] Real dev DB may already be at alembic head (0024) -- migrations 0023/0024 were applied there accidentally via the Windows .venv during this plan's session (WSL env-var isolation). Plan 39-06 should run 'alembic current' first before assuming it needs to apply them fresh.
- [Phase 39, Plan 06] Checkpoint NOT approved -- operator found: (1) the separator dot between birth/death dates and between president/party renders with no visible spacing, hard to read; (2) overall popover styling diverges from the Figma mockups (`popover - Bench.png`/`popover-Advocate.png`) -- tenure rows should be two-column (bold title left, year range right-aligned) but render as a single em-dash line; (3) Bio & Photo save silently fails -- the input retains typed text until refresh, masking that nothing was persisted. Step 6 (identical treatment across party values, the one explicitly blocking acceptance criterion) was separately confirmed by the operator as passing -- no apolitical-constraint violation. See `39-06-SUMMARY.md` for full detail. Needs `/gsd-plan-phase 39 --gaps` before this phase can close.
- [Phase 39, Plan 07] 39-07-PLAN.md's Task 1 verify gate '! grep -q "Non-critical" +page.server.ts' has one pre-existing, unrelated false-positive match at the load() function's merge-picker fetch (a read, not a write) -- not a regression, documented in 39-07-SUMMARY.md's Issues Encountered. No action needed unless a future plan wants to rename that unrelated comment.

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

Last session: 2026-07-29T01:29:16.827Z
Stopped at: Completed 39-08-PLAN.md (bench popover mockup-fidelity gap closure)
Resume file: None

## Operator Next Steps

- Run $gsd-verify-work 35 to validate the completed capability removal, or continue the already-prepared Phase 37 design work.
