---
gsd_state_version: 1.0
milestone: v1.7
milestone_name: Corpus Fidelity & Resolve Rework
current_phase: 41
current_phase_name: canonical-corpus-fixture-selection
status: executing
stopped_at: Completed 41-01-PLAN.md
last_updated: "2026-07-29T22:37:48.285Z"
last_activity: 2026-07-29
last_activity_desc: Phase 41 execution started
progress:
  total_phases: 5
  completed_phases: 0
  total_plans: 3
  completed_plans: 1
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-29 after starting v1.7 milestone)

**Core value:** Anyone can open a SCOTUS oral argument and immediately follow the conversation — the chat format makes speaker identity, turn-taking, and flow self-evident without legal background.
**Current focus:** Phase 41 — canonical-corpus-fixture-selection

## Current Position

Phase: 41 (canonical-corpus-fixture-selection) — EXECUTING
Plan: 2 of 3
Status: Ready to execute
Last activity: 2026-07-29 — Phase 41 execution started

**Milestone shape:**

| Phase | Name | Requirements | Depends on |
|-------|------|--------------|------------|
| 41 | Canonical Corpus Fixture Selection | CORPUS-12 | — |
| 42 | Corpus Import Fidelity Diff & Fix | CORPUS-13, CORPUS-14 | 41 |
| 43 | Dev-Only Reset to Fixture | DEVTOOL-01, DEVTOOL-02 | 41 |
| 44 | Resolve Table Rework | RESOLVE-01–06 | — (parallel) |
| 45 | Deferred UI Bug Fixes | BUG-01, BUG-02 | — (parallel) |

Phases 44 and 45 are independent of the corpus track and of each other; 41 is a gated operator-confirmation phase that both 42 and 43 read from.

## Deferred Items

Items deferred at v1.6 close on 2026-07-29, and where they landed in v1.7:

| Category | Item | Status |
|----------|------|--------|
| todo | 2026-07-28-unpublished-argument-visible-in-cases-list.md (bug) | absorbed → BUG-01, Phase 45 |
| todo | 2026-07-29-popover-scrollbar-outside-card.md (ui) | absorbed → BUG-02, Phase 45 |
| seed | SEED-001-rework-resolve-table-requirements | surfaced and absorbed → RESOLVE-01–06, Phase 44 |

Still open from earlier milestones:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| backlog | Phase 999.9 — edit affordance on utterances + speaker popover | backlog (todo file moved to `todos/completed/`, tracked as 999.9) | 2026-07-13 |
| backlog | Phases 999.2–999.8 | out of v1.7 scope; candidates for `/gsd-review-backlog` | 2026-07-12 |
| verification | 01/03/04-VERIFICATION.md | human_needed (stale — human UAT completed per commits) | 2026-06-15 |
| verification | 11-VERIFICATION.md | human_needed (v1.2 carry-over — Argument Metadata Editing human UAT never formally closed) | 2026-06-29 |
| context_question | Phase 999.2 (999.2-CONTEXT.md, 3 open questions) | not started | 2026-07-12 |

## Performance Metrics

- v1.5: 10 phases, 55 plans, 10 days (2026-07-02 → 2026-07-12)
- v1.6: 11 phases, 51 plans, 17 days (2026-07-12 → 2026-07-29)
- v1.7: 5 phases, plans TBD — started 2026-07-29

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| — | — | — | — |
| Phase 41 P01 | 2h32m | 2 tasks | 1 files |

v1.5/v1.6 per-plan metrics cleared at this milestone boundary per the standard STATE.md reset; the underlying per-plan SUMMARY files remain in `.planning/milestones/v1.5-phases/` and `.planning/milestones/v1.6-phases/`.

## Accumulated Context

### Decisions

Full cross-milestone decision log lives in PROJECT.md's Key Decisions table. Per-phase decisions for v1.6 (Phases 31–40.1) are archived in `.planning/milestones/v1.6-phases/*/`-SUMMARY.md and `.planning/milestones/v1.6-ROADMAP.md`; cleared here at milestone close per the standard STATE.md reset.

**Carry-forward constraints that v1.7 planning must respect:**

- [Phase 29 → affects Phase 42]: The ConvoKit importer applies a *positive apolitical allow-list*, not a blocklist — partisan/outcome fields are dropped by design and SCDB data is never imported. Phase 42's fidelity diff must classify these as intentional exclusions, not as importer defects to "restore."
- [Phase 29 CR-01 → affects Phase 42/43]: `question_number` is derived per-docket via `select(func.max(...))` against the real `(source_docket, question_number)` UNIQUE constraint. Any reseed or re-import path must preserve that derivation, not hardcode `1`.
- [Phase 30 → affects Phase 43]: Corpus-imported arguments must land at `status=PIPELINE` paired with a PAUSED/RESOLVE `AdminJob`, or they are unpublishable. A reseed that skips this reproduces the bug Phase 30 fixed.
- [Phase 27 Plan 11 → affects Phase 44]: Use the write-only `$state` reassignment pattern for any effect-driven reset in Svelte 5 — an effect that both reads and writes the same `$state` inside its own body triggers `effect_update_depth_exceeded`.
- [Phase 27 CR-01/CR-02 → affects Phase 44]: Keep data-carrying form inputs always present in the DOM (outside `{#if}` blocks); conditionally-rendered inputs silently don't submit and wipe data on save.
- [Phase 36 + CLAUDE.md Architecture Rule 4 → affects Phase 44/RESOLVE-05]: Extracted-value hints use the shared `CopyableExtractedValue` component (Phase 38 added its stacked provenance mode) — RESOLVE-05's "Extracted: …" hints should reuse it rather than hand-rolling a fifth variant.
- [Phase 31 → affects every phase]: The test suite runs against `scotus_test` via `TEST_DATABASE_URL`, and a `pytest_sessionfinish` hook fails any run that changes shared-dev-DB `people`/`arguments` row counts. Phase 43's destructive reset must never be exercised against the shared dev DB from a test.
- [Phase 41 Plan 01 → affects Phase 41 Plan 02/03]: Full-corpus run supersedes RESEARCH.md's exploratory pick: conversation 15169 (Baltimore & Ohio Railroad Co.) is the real 3/4-coverage top candidate, not 14837 (Permian Basin, 2/4); 14969 (Shapiro v. Thompson) ties 15169 at 3/4 as the named runner-up for Plan 03's operator confirmation.

### Roadmap Evolution

v1.6's roadmap evolution is archived in `.planning/milestones/v1.6-ROADMAP.md`. Cleared here at milestone close.

2026-07-29: v1.7 roadmap created — Phases 41–45 derived from the milestone's 13 requirements (CORPUS-12–14, DEVTOOL-01–02, RESOLVE-01–06, BUG-01–02). Numbering continues from v1.6's last phase (40.1). Coverage 13/13, no orphans, no duplicates. CORPUS-12 was given its own gate phase (41) rather than folded into the diff work so fixture selection is an explicit operator confirmation, and so Phase 43 can depend on the fixture without depending on Phase 42's importer fixes.

2026-07-29: During Phase 41 discuss-phase, CORPUS-12 widened from a single canonical fixture to a 4-fixture set: 1 structurally-complex argument (unchanged — still the sole target of Phase 42's diff/fix work) plus 3 additional arguments chosen for publish/pipeline-state variety (unpublished/DRAFT, published, mid-pipeline) so Phase 43's reset tool and Phase 45's publish/unpublish bug work have real states to exercise. ROADMAP.md Phase 41/42/43 goals and success criteria updated; REQUIREMENTS.md CORPUS-12/DEVTOOL-01 updated to match. Also surfaced but explicitly deferred: renaming "Case" to "Argument" across DB schema/routes/frontend — logged in REQUIREMENTS.md Out of Scope, not actioned this milestone.

### Pending Todos

- None unassigned. Both previously-pending todos (`2026-07-28-unpublished-argument-visible-in-cases-list.md`, `2026-07-29-popover-scrollbar-outside-card.md`) are now covered by Phase 45 (BUG-01 / BUG-02) and should be moved to `todos/completed/` when that phase verifies.

### Blockers/Concerns

**Directly relevant to v1.7:**

- **[affects Phase 43 — DEVTOOL-01]** `api/services/admin_arguments.py::delete_argument` omits `argument_status_log` from its FK cascade (found during Phase 31 Plan 04). Deleting a DRAFT argument that has a status-log row likely raises `ForeignKeyViolation`. Phase 43's full wipe will hit this on essentially every argument — expect to fix or work around it as part of that phase, not discover it at execution time.
- **[affects Phase 42/43]** The real dev DB is believed to be at alembic head `0024` (migrations 0023/0024 were applied there via the Windows `.venv` during Phase 39 Plan 02). Run `alembic current` before assuming a migration needs applying.
- **[affects Phase 44]** SEED-001's mockup image (`resolve-speakers-panel.png`) lives outside the repo at `C:\workspace\scotuschat\resolve-speakers-panel.png`. Re-request/re-attach it at Phase 44 discuss/plan time if it is no longer on disk — the written deltas in the seed are detailed, but the visual is the acceptance reference.

**Deployment blockers (v1.4, unresolved — explicitly out of v1.7 scope):**

- `BODY_SIZE_LIMIT=10M` must be set in DO App Platform env
- `ORIGIN`, `PROTOCOL_HEADER`, `HOST_HEADER` env vars required on DO
- `admin.scotuschat.com` DNS entry must be created before smoke test

**Process concern carried from Phase 40.1 (PROJECT.md Key Decisions, ⚠️ Revisit):**

- When a fix for a previously-diagnosed issue lands via a commit outside the formal plan sequence, flip the source debug session's / verification's `status` field in that same commit. v1.6 lost a phase slot (40.1) to a stale `diagnosed` status; no structural fix shipped.

## Session Continuity

Last session: 2026-07-29T22:37:47.696Z
Stopped at: Completed 41-01-PLAN.md
Resume file: None

## Operator Next Steps

- Review `.planning/ROADMAP.md` (v1.7 section) and `.planning/REQUIREMENTS.md` traceability.
- Then `/gsd-discuss-phase 41` to gather context for the fixture-selection gate.
- Phases 44 and 45 are independent of the corpus track — either can be started in parallel if you'd rather begin with the Resolve rework or the bug fixes.
