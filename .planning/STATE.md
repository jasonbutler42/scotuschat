---
gsd_state_version: 1.0
milestone: v1.5
milestone_name: Admin Screens Cleanup
current_phase: 27
current_phase_name: People Admin
status: verifying
stopped_at: Completed 26-05-PLAN.md (gap closure)
last_updated: "2026-07-08T19:53:27.742Z"
last_activity: 2026-07-08
last_activity_desc: Phase 26 complete, transitioned to Phase 27
progress:
  total_phases: 7
  completed_phases: 5
  total_plans: 25
  completed_plans: 25
  percent: 71
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-07 after Phase 25 completion)

**Core value:** Anyone can open a SCOTUS oral argument and immediately follow the conversation — the chat format makes speaker identity, turn-taking, and flow self-evident without legal background.
**Current focus:** Phase 27 — People Admin

## Current Position

Phase: 27 — People Admin
Plan: Not started
Status: Phase complete — ready for verification
Last activity: 2026-07-08 — Phase 26 complete, transitioned to Phase 27

Progress: [██████████] 100%

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

### Pending Todos

None currently tracked.

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

## Session Continuity

Last session: 2026-07-08T19:53:00Z
Stopped at: Phase 26 complete (force-advanced past 2 accepted UAT items — see 26-VERIFICATION.md Acknowledged Gaps), ready to plan Phase 27
Resume file: None
