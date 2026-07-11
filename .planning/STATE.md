---
gsd_state_version: 1.0
milestone: v1.5
milestone_name: Admin Screens Cleanup
current_phase: 28
current_phase_name: dashboard
status: executing
stopped_at: Completed 28-02-PLAN.md
last_updated: "2026-07-11T12:44:29.050Z"
last_activity: 2026-07-11
last_activity_desc: Phase 28 execution started
progress:
  total_phases: 9
  completed_phases: 8
  total_plans: 52
  completed_plans: 51
  percent: 89
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-09 after Phase 27 completion)

**Core value:** Anyone can open a SCOTUS oral argument and immediately follow the conversation — the chat format makes speaker identity, turn-taking, and flow self-evident without legal background.
**Current focus:** Phase 28 — dashboard

## Current Position

Phase: 28 (dashboard) — EXECUTING
Stage: Ready to plan
Plan: 3 of 3
Status: Ready to execute
Last activity: 2026-07-11 — Phase 28 execution started

Progress: [████████████████████] 36/36 plans (100%). Phase 27 is now fully verified complete: 5th UAT retest passed all 7 items (including the CR-01/CR-02 data-preservation round-trips previously blocked by the effect_update_depth_exceeded regression), 27-SECURITY.md shows threats_open: 0, and 27-VERIFICATION.md status is canonically `passed`. `completed_phases` in this file's frontmatter is correctly at 6/7 (86%).

## Performance Metrics

Velocity carried from v1.4: ~40 min/plan average. v1.5 phases not yet started.

*Updated after each plan completion*

## Accumulated Context

### Decisions

Full log in PROJECT.md Key Decisions table. Key decisions entering v1.5:

- [v1.4]: `delete_argument` FK cascade order: Utterance → PipelineRun → ArgumentParticipant → CaseArgument → NULL AdminJob → Argument
- [v1.4]: `AdminSubNav` + `TopNav variant=public` pattern established for admin layout (NAV-02)
- [v1.4]: Migration 0008 commits Alembic transaction before ALTER TYPE ADD VALUE — required pattern for future PG enum expansions (applies to Phase 22 `unpublished` value)
- [v1.4]: SideEnum.ADVOCATE retained as legacy value; code never produces it going forward — same discipline needed for any new enum values
- [Phase ?]: 22-01: Backfill uses status::argument_status; unpublished enum value retained (PG cannot remove enum values)
- [Phase ?]: 22-01: ArgumentStatusLog minimal schema (D-06) — no previous_status, notes, or triggered_by in v1.5
- [Phase ?]: Migration 0013: court_tenures.appointed_by column rename-by-move from people.appointing_president; no backfill (D-08)
- [Phase ?]: 23-01: ParseStats expanded with flat cover_metadata fields; speaker_count retained for TS backward compat
- [Phase ?]: 23-01: MetadataUpdate.question_number free text; service parses to int with guarded try/except (T-23-02)
- [Phase ?]: 23-01: question_number from Argument.question_number column only (NOT cover_metadata)
- [Phase ?]: 23-02: ArgumentDetailsCard owns its own use:enhance form; action prop drives save target; update({reset:false}) mandatory on success to preserve pill $state
- [Phase ?]: 23-03: saveJobMetadata derives argument_id server-side; parse stats source from ps.* (cover_metadata passthrough)
- [Phase ?]: 23-04: Empty-string sentinel distinguishes operator-cleared dockets from unsent field; service converts to None
- [Phase ?]: 23-04: hints.question_number frozen to null in load() — Argument.question_number is operator-editable, not an immutable extraction source
- [Phase ?]: 23-05: Docket pill max-count guard — client UX convenience; CR-02 server guard is authoritative
- [Phase 24]: Removed the list_jobs limit parameter entirely instead of making it optional, matching PLIST-03 and D-10. — PLIST-03 requires all pipeline runs, and D-10/D-12 explicitly remove the cap with no pagination UI for this phase.
- [Phase ?]: 24-02: DocketPillInput id prop defaults to 'docket-input' to preserve ArgumentDetailsCard's existing label/for wiring; list page can override to avoid duplicate-id conflicts
- [Phase 24-03]: effectiveDockets state replaces the old direct pills state as the parent-owned docket source of truth, keyed via effectiveDockets.join to force DocketPillInput to re-seed from initialValues on failed-save restoration — D-04 requires ArgumentDetailsCard to consume the shared DocketPillInput component while preserving Phase 23 failed-save state restoration
- [Phase ?]: 24-04: D-07 supersession — full docket list carried via admin_jobs.source_dockets (run-start metadata) instead of an immediate metadata PATCH, since argument_id is null until ingest completes
- [Phase ?]: 24-04: rerun_job copies original.source_dockets onto the new job so reruns preserve the originally submitted docket list
- [Phase ?]: 24-05: Rejection guard lives inside a single nested _add(raw) helper in _normalize_dockets (T-24-08) — both primary_docket and source_dockets share identical strip/dedupe/reject logic
- [Phase ?]: 24-05: pipeline/__main__.py startup guard wraps parser.parse_args() in try/except SystemExit, scrapes --job-id from argv, and writes a bounded (message[:500]) best-effort FAILED status before re-raising — runs entirely inside the child process, pipeline_spawn.py and fire-and-forget invariant D-01 unchanged
- [Phase ?]: 25-01: get_job_readiness treats already_created as a short-circuit on argument.status != PIPELINE, independent of any other blocker (D-01, D-04, D-18, D-20)
- [Phase ?]: 25-01: update_resolve_row_for_job is a new job-scoped mutation (not a reuse of admin_arguments.update_participant_side, which rejects BENCH by design) — forces title null whenever side == BENCH (D-14, D-18, D-19, PJOB-14, PJOB-18, PJOB-15)
- [Phase ?]: 25-01: create_person_for_job validates the target ArgumentParticipant belongs to the job's own argument BEFORE creating any Person row (validate-before-mutate IDOR guard, D-12, PJOB-19)
- [Phase ?]: 25-02: title_hint is sourced from the same ArgumentParticipant.title column as title (no separate stored extraction snapshot exists for advocate title, unlike cover_metadata for argued_date/docket)
- [Phase ?]: 25-02: _bench_role_and_missing_tenure is a new Phase-25-specific helper (no fallback to most-recent tenure) — intentionally distinct from speakers._tenure_role_name's D-14 fallback used by the public speaker popover
- [Phase ?]: 25-02: list_resolve_rows_for_job raises ValueError for missing job/unlinked argument (not None), matching admin_jobs.py's established pattern so the router maps it to 422
- [Phase 25]: 25-03: Missing router endpoints for get_job_readiness/get_failed_step_recovery were added under Rule 3 auto-fix (GET /jobs/{job_id}/readiness, GET /jobs/{job_id}/failed-recovery), mapping ValueError to 422 to match sibling resolve-rows endpoints
- [Phase 25]: 25-03: readonlyMode computed once in +page.server.ts load() (argument.status !== 'pipeline') so RunStatusCard/ResolveCard/ArgumentDetailsCard read the same boolean in Plan 25-04
- [Phase 25]: 25-03: saveResolveRow action never accepts a client-supplied argument_id; job_id route param is the only trust boundary, argument ownership re-derived server-side in the FastAPI PATCH handler (T-25-16)
- [Phase 25]: 25-04: Argument Role is read-only in ResolveCard, derived entirely from the Bench/Advocate side value — backend ResolveRowUpdate only writes side/title, so there is no separate role field to edit
- [Phase 25]: 25-04: Person re-matching (Confirm/Select/Create person) only appears while job.status is paused via the unchanged ?/resolve batch action; Resolved-as becomes read-only display afterward while side/title remain editable via saveResolveRow
- [Phase 25]: 25-04: Preserved Danger Zone markup/confirmation text verbatim per D-09/D-22, superseding the UI-SPEC's Destructive confirmation copy row for this phase
- [Phase ?]: 26-01: publish/unpublish guards key on Argument.status not published_at; re-publish from UNPUBLISHED allowed (D-02/AEDIT-08)
- [Phase ?]: 26-01: unpublish_argument preserves published_at (no longer nulled) so Status card can show last-published date
- [Phase ?]: 26-01: ArgumentStatusLog writes inlined at 3 call sites (no shared helper) to avoid admin_jobs -> admin_arguments import cycle (D-10)
- [Phase ?]: 26-01: delete_argument gate and update_argument slug-freeze both switched from published_at to status-keyed checks (ALIST-01, D-03/AEDIT-09)
- [Phase 26-03]: Row actions key on arg.status (draft/unpublished -> Publish, published -> Unpublish) instead of the old published_at-based check, matching Plan 26-01's backend status model
- [Phase 26-03]: RunStatusCard's Archived override lives only in the badgeColor/badgeLabel derivations — BADGE_COLOR/BADGE_LABEL maps stay keyed purely on jobStatus
- [Phase ?]: 26-02: list_argument_speakers is a new argument-scoped helper (not a reuse of job-scoped list_resolve_rows_for_job); unresolved bench rows report missing_tenure=False (no person to flag); title_hint sources the same ArgumentParticipant.title column as title (D-06); update_participant_side writes title only when provided so omitting it never clobbers a saved title
- [Phase ?]: 26-04: can_delete changed from status !== 'published' to status === 'draft', matching Plan 26-01's backend gate exactly (Published AND Unpublished both blocked)
- [Phase ?]: 26-04: Publish/Unpublish moved into the Status card body (status-driven three-way branch) instead of a standalone floating block between Advocate Roles and Danger Zone
- [Phase ?]: 26-04: Status history rendered as its own card directly below Status, not a nested sub-section, per UI-SPEC planner-discretion note
- [Phase ?]: delete_argument gate rewritten to a single positive status == DRAFT condition so PIPELINE is now blocked too (T-26-13)
- [Phase ?]: update_participant_side gained a pre-SELECT guard rejecting UNKNOWN/legacy ADVOCATE alongside the existing BENCH guard (T-26-14, AEDIT-06)
- [Phase ?]: 26-06: is_archived defaults to False on get_job (detail) path since RunStatusCard derives its archived signal from RunReadiness.state == 'already_created', not this field
- [Phase ?]: 26-06: list_jobs() selects Argument.status as a scalar column via outerjoin rather than eager-loading the Argument relationship, avoiding N+1 while deriving is_archived per row
- [Phase 26]: Phase 26 marked complete with two UAT items accepted as non-blocking rather than fixed: Test 18's own result line stays "issue" as historical record (its retest, Test 27, passed and is the authoritative outcome — see 26-VERIFICATION.md Acknowledged Gaps); Test 26 (Unresolved-advocate visual check) is a deliberate deferral pending the SEED-001 Resolve/Speakers table rework, not a defect
- [Phase 26]: 26-REVIEW.md's 3 new Critical findings (CR-01 rerun/local-upload, CR-02 blank metadata validation, CR-03 unique-constraint collision) were all traced via git blame to Phase 11/19/pre-existing code, unrelated to Phase 26's changes — recommended as backlog items, not phase gaps
- [Phase 27]: 27-01: Person.birthdate added via migration 0016 chained to head 0015, no backfill; Death Date and reason-left-the-bench columns explicitly deferred (D-12/D-14)
- [Phase 27]: 27-01: role_id/role_name removed from PersonUpdate/PersonDetail/PersonListItem (D-10); new PersonCreateRequest requires only full_name + is_justice (D-08); TenureRow gains per-row appointed_by/appointing_president_party (D-16)
- [Phase 27]: 27-02: _missing_fields branches on Person.is_justice with no role_id check; list_people signature changed to (db, is_justice=None, missing=None, tenure_gaps=False), dropping the Role outerjoin entirely (D-10)
- [Phase 27]: 27-02: has_tenure_gap reuses the tenure_gaps filter's BENCH-side gap-detection subquery verbatim, keyed on ArgumentParticipant.side not on the row's current is_justice flag
- [Phase 27]: 27-03: get_person_detail/update_person drop the person-level Role join/write entirely (D-10); update_person writes birthdate via the same empty-string-to-None normalization used for bio_text/photo_url
- [Phase 27]: 27-03: create_person is a general, unscoped create (no pipeline-run lookup, no participant-row linkage) modeled on admin_jobs.create_person_for_job with all job-scoping stripped; POST /people inherits the router-level admin-auth dependency with no additional guard (D-09)
- [Phase 27]: 27-03: Rule-1 auto-fix -- GET /people's list_people call updated from the removed (incomplete, tenure_gaps) signature to the current (is_justice, missing, tenure_gaps) signature Plan 27-02 had already introduced
- [Phase ?]: 27-04: Tab switch clears missing/tenure_gaps filters — both are tab-scoped concepts (missing-field vocab differs per tab; tenure_gaps is Bench-only)
- [Phase ?]: 27-04: Bench/Advocate segmented toggle uses aria-pressed (not role=tab/tablist), matching the existing pill-button ARIA idiom rather than adding a keyboard-nav tablist contract
- [Phase 27-05]: Split combined Bio & Photo card into separate Photo/Biography cards but kept one ?/photo form (bio_text still saves with photo, Pitfall 7 extended unchanged)
- [Phase 27-05]: TenureRow.seat retained in state/payload with no UI input (D-18 field list omits it) to avoid wiping existing seat data on save
- [Phase 27-05]: Breadcrumb + Cancel target derived from data.person.is_justice at load time (backTab), not the live Bench/Advocate toggle state
- [Phase 27-05]: Save Person/Cancel action row moved to bottom of page (after Merge/Delete) per UI-SPEC card order item 8
- [Phase 27-05]: Removed dead roles-building loop/RoleItem/role_id/role_name from +page.server.ts load() and types, completing D-10's full Role removal
- [Phase ?]: 27-06: Photo and Biography cards both omitted on the create route (not just Photo) -- they share a single ?/photo form/action on [id] that has no analog on this route, and D-08 excludes bio/photo from the create payload
- [Phase ?]: 27-06: isJustice starts as boolean|null (not defaulting to false) so neither Bench nor Advocate is pre-selected on /admin/people/new, matching D-08's explicit-choice requirement
- [Phase ?]: 27-06: Merge/Delete markup, state, and fetchMergePreview removed entirely from the create page (not just guarded) since this route has no merge/delete actions for those forms to target
- [Phase ?]: 27-07: Fixed all four middle columns (Bench Tenure coverage/gap plus Advocate Argument count/Missing fields), not just the reported Advocate pair -- Bench tab had the identical latent zero-horizontal-padding defect.
- [Phase ?]: 27-08: create_person now sets first_name/middle_name/last_name/name_suffix from PersonCreateRequest, normalizing blank strings to None (matches update_person's Pitfall 5 convention); fixed as a bug (parity with [id] editor), not a D-08 scope amendment
- [Phase 27-09]: D-16 amendment (2026-07-09): appointing_president_party reversed from free-text to a curated select scoped to that field only; appointed_by remains free-text; Seat-as-toggle deferred to backlog Phase 999.16
- [Phase 27-10]: Relocated hidden birthdate/tenures inputs outside {#if isJustice} (CR-01) and completed the person-id-change reset effect to re-derive tenureRows/nextKey (CR-02), closing PEDIT-07's data-preservation gap
- [Phase 27]: 27-11: Used a plain local resetKey counter (not $state) inside the person-id-change reset $effect, writing nextKey once after the .map() completes, matching the codebase's write-only reset-effect convention — Fixes effect_update_depth_exceeded regression from 27-10 CR-02 without altering CR-01/CR-02 behavior
- [Phase 27]: Phase closed out with a 5th UAT retest (7/7 passed) after the 27-11 fix unblocked the previously-stuck 4th retest; 27-REVIEW.md's one Critical finding (CourtTenure rows unaccounted for in merge/delete FK bookkeeping, api/services/admin_people.py) predates Phase 27 (Phase 22) and was scoped out as a backlog item, not a phase gap
- [Phase ?]: 29-01: Migration 0017 down_revision confirmed as 0016 via live alembic heads before writing the file (no branched history)
- [Phase ?]: 29-01: python-dateutil package legitimacy checkpoint approved by human (PyPI source repo, version, exact package name all confirmed) before install
- [Phase 29-02]: detect_stage_direction requires the ENTIRE utterance text be a single bracket/paren token before any vocabulary match, ruling out embedded parenthetical citations mid-sentence without extra heuristics
- [Phase 29-02]: apolitical.py field lists sourced from 29-CONTEXT.md's verified real cases.jsonl/conversations.json field names (title/petitioner/respondent/...) rather than the plan's illustrative title/case_name shorthand
- [Phase ?]: 29-03: reconstruct_full_name is a plain concatenation (no punctuation synthesis needed) since the CSV's Middle Name or Initial column already embeds the trailing period for single-initial values; no MANUAL_NAME_OVERRIDES entries were needed for the 13 seeded justices
- [Phase ?]: 29-03: court_tenures.seat for CSV-imported justices uses the CSV section header text itself (Chief Justice / Associate Justice), per RESEARCH.md Open Question 2
- [Phase ?]: 29-03: Task 2 integration tests use a dedicated per-test engine/session fixture (isolated_session) instead of conftest.py's shared session-scoped engine fixture, avoiding a pre-existing Windows asyncpg/pytest-asyncio stale-event-loop failure without touching conftest.py
- [Phase 29-06]: oyez_transcript_id is the only corpus-sourced signal added to the public payload (no outcome/vote data), preserving apolitical constraint on public surface
- [Phase 29-06]: Per-argument attribution note visibility computed server-side in +page.server.ts, never in browser code (Architecture Rule 2)
- [Phase 29]: 29-04: conversations.json-to-cases.jsonl join key is case_id equality (not docket matching) -- cases.jsonl carries its own case_id field matching the conversation key; a secondary case_id index is built locally from load_cases' docket-indexed values
- [Phase 29]: 29-04: speaker-resolution helpers (_resolve_person/_resolve_and_link_participant) are generic and reused unchanged by Plan 05 -- this plan only wires them to conversations.json's advocates dict (the sole per-conversation participant source before utterances.jsonl is streamed)
- [Phase 29]: 29-05: per-conversation resolved_participants cache shared between advocates-dict resolution and utterance-speaker resolution -- avoids inflated people_matched counts and redundant DB round trips for speakers with many turns
- [Phase 29]: 29-05: stage-direction row-splitting reconciles D-16/D-18 via one algorithm -- split turn text on \n, classify each segment with detect_stage_direction, rejoin contiguous non-marker segments; handles whole-turn markers and inline mid-turn markers with no re-implemented regex
- [Phase 29]: 29-05: counters split from Plan 04's single 'flagged' bucket into speakers_flagged/conversations_errored plus new people_created/people_matched/utterances_created/stage_direction_utterances_created/utterance_rows_errored, all via counters.get(key,0)-safe increments (D-14 per-batch summary)
- [Phase 29-07]: No service-layer change needed; api/services/arguments.py and api/services/cases.py already pass argued_date through with no coercion once the schema accepts None
- [Phase 29-07]: New DB-gated test calls get_argument_with_utterances() directly, avoiding the api.main HTTP client path affected by the pre-existing FastAPI test lifespan/session-factory failure
- [Phase 29-07]: CaseItem.argued_date fixed proactively even though unreachable today (get_cases() filters published_at IS NOT NULL) to avoid a second gap-closure round
- [Phase 29-08]: Relabeled import_convokit.py's single per-argument PipelineRun.step from ingest to parse, matching api/services/arguments.py's established read-side contract (step==parse filter) -- fixed the write side rather than adding a second query branch to a shared read contract
- [Phase 29-08]: New end-to-end test calls get_argument_with_utterances directly (no HTTP client, no api.main import), avoiding the pre-existing FastAPI test lifespan/session-factory failure, consistent with 29-07's established pattern
- [Phase 29-09]: docket_question_conflict counted and printed distinctly from conversations_errored so an operator can tell a data-loss-prevented collision apart from an unrelated malformed-row error — IntegrityError handling kept as defense-in-depth only -- the primary fix is _next_question_number aligning the write path with the DB's real (source_docket, question_number) constraint before any flush is attempted
- [Phase ?]: 30-01: Argument.status write flipped from DRAFT to PIPELINE in _import_conversation (D-06 superseded per 30-RESEARCH.md Pitfall 1)
- [Phase ?]: 30-01: AdminJob insertion placed immediately after _import_utterances returns -- bench Justice participants are only discovered while streaming utterances
- [Phase ?]: 30-01: _build_discrepancies() built from ArgumentParticipant rows, mirroring resolve.py's exact 7-key HIT shape so ResolveCard.svelte renders unmodified for corpus jobs
- [Phase ?]: 30-01: No separate commit/flush or create_job() reuse for the AdminJob insert -- get_session()'s context manager commits the whole per-conversation transaction atomically
- [Phase 30]: 30-02: get_job()'s exists() correlates on the already-loaded job.argument_id Python value (not a second AdminJob-correlated subquery) since a single-row lookup has no need to join back to AdminJob
- [Phase 30]: 30-02: PIPELINE_RUN_STRATEGY imported from pipeline.commands.import_convokit into api/services/admin_jobs.py, following the established cross-layer import precedent (normalize_label)
- [Phase 30-03]: Visual verification (Task 2) completed via direct dev-database inspection because the dev DB currently has zero corpus-imported AdminJob rows (they predate 30-01's paired-AdminJob insert); full Corpus-tag confirmation deferred to plan 30-04's wipe-and-rerun
- [Phase 30-04]: D-02 upheld: term-1955 corpus wipe-and-rerun delivered with zero committed code — ad hoc FK-safe scoped wipe SQL plus re-run of the existing idempotent import-justices/import-convokit CLI; no migration/backfill script added.
- [Phase 30-04]: Mid-execution test-data-leakage blocker (duplicate Ketanji Brown Jackson Person row from leaked pytest fixture commits) resolved via its own scoped DELETE, separate from this plan's convokit_import-scoped wipe; underlying test-isolation defect escalated to ROADMAP.md backlog Phase 999.19 rather than fixed in-plan.
- [Phase 28]: 28-01: get_tenure_gap_justices delegates to existing list_people(is_justice=True, tenure_gaps=True) rather than duplicating the private gap_person_ids_query subquery
- [Phase 28]: 28-01: get_people_stats/get_incomplete_people call list_people(db) unfiltered and count/slice in Python — no new SQL filter surface (D-05)
- [Phase 28]: 28-01: get_recent_drafts orders by Argument.id DESC (not resolved_at) — Argument has no created_at column (Pitfall 3)
- [Phase 28]: 28-02: GET /utterances/count placed adjacent to /arguments/stats and /arguments/recent-drafts (no {id}-sibling ordering constraint applied)
- [Phase 28]: 28-02: Route test file omits client_no_db/401 auth-gate tests -- Task 2 scope is proving 200-not-422 resolution and response shape, router auth inheritance already covered elsewhere

### Roadmap Evolution

- Phase 29 added: Historical Corpus Import — bulk-import ~7,800 historical oral arguments (terms 1955-2019) from the Cornell ConvoKit supreme-corpus dataset, bypassing PDF/LLM parsing for this batch; depends on Phase 28

### Pending Todos

- `2026-07-08-edit-affordance-on-utterances-and-speaker-popover.md` (ui) — authenticated "Edit" affordance on every utterance + on the speaker popover card; no phase assigned yet

### Blockers/Concerns

Deployment blockers (v1.4, unresolved — not in v1.5 scope):

- `BODY_SIZE_LIMIT=10M` must be set in DO App Platform env
- `ORIGIN`, `PROTOCOL_HEADER`, `HOST_HEADER` env vars required on DO
- `admin.scotuschat.com` DNS entry must be created before smoke test

## Deferred Items

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

## Session Continuity

Last session: 2026-07-11T12:44:29.035Z
Stopped at: Completed 28-02-PLAN.md
Resume file: None
