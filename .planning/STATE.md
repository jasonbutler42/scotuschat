---
gsd_state_version: 1.0
milestone: v1.5
milestone_name: Admin Screens Cleanup
current_phase: 22
current_phase_name: schema-foundations
status: executing
stopped_at: Completed 22-02-PLAN.md
last_updated: "2026-07-02T19:30:04.396Z"
last_activity: 2026-07-02
last_activity_desc: Phase 22 execution started
progress:
  total_phases: 7
  completed_phases: 0
  total_plans: 3
  completed_plans: 2
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-02 after v1.5 milestone start)

**Core value:** Anyone can open a SCOTUS oral argument and immediately follow the conversation — the chat format makes speaker identity, turn-taking, and flow self-evident without legal background.
**Current focus:** Phase 22 — schema-foundations

## Current Position

Phase: 22 (schema-foundations) — EXECUTING
Plan: 3 of 3
Status: Ready to execute
Last activity: 2026-07-02 — Phase 22 execution started

Progress: [░░░░░░░░░░] 0%

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

### Pending Todos

None active. v1.4 todos closed at milestone.

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

## Session Continuity

Last session: 2026-07-02T19:30:04.386Z
Stopped at: Completed 22-02-PLAN.md
Resume file: None
