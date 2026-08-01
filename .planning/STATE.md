---
gsd_state_version: 1.0
milestone: v1.7
milestone_name: Corpus Fidelity & Resolve Rework
current_phase: 44
current_phase_name: resolve-table-rework
status: executing
stopped_at: Completed 44-02-PLAN.md
last_updated: "2026-08-01T18:21:47.044Z"
last_activity: 2026-08-01
last_activity_desc: Phase 44 execution started
progress:
  total_phases: 5
  completed_phases: 3
  total_plans: 16
  completed_plans: 14
  percent: 60
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-29 after starting v1.7 milestone)

**Core value:** Anyone can open a SCOTUS oral argument and immediately follow the conversation — the chat format makes speaker identity, turn-taking, and flow self-evident without legal background.
**Current focus:** Phase 44 — resolve-table-rework

## Current Position

Phase: 44 (resolve-table-rework) — EXECUTING
Plan: 3 of 4
Status: Ready to execute
Last activity: 2026-08-01 — Phase 44 execution started

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
| Phase 41 P02 | 9min | 2 tasks | 1 files |
| Phase 41 P03 | 12min | 2 tasks | 1 files |
| Phase 42 P01 | 25min | 2 tasks | 5 files |
| Phase 42 P02 | 26min | 3 tasks | 3 files |
| Phase 42 P03 | 29min | 3 tasks | 4 files |
| Phase 42 P04 | 38min | 3 tasks | 6 files |
| Phase 42 P05 | 35min | 3 tasks | 2 files |
| Phase 43 P01 | 25min | 3 tasks | 8 files |
| Phase 43 P02 | 45min | 2 tasks | 2 files |
| Phase 43 P03 | 40min | 3 tasks | 3 files |
| Phase 44 P01 | 36min | 3 tasks | 19 files |
| Phase 44 P02 | 21min | 3 tasks | 2 files |

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
- [Phase ?]: Phase 41 Plan 02: Recommendation confirmed as conversation 15169 (Baltimore & Ohio Railroad Co. v. United States) at 3/4 coverage, with 14969 (Shapiro v. Thompson) as the named tied runner-up, superseding RESEARCH.md's earlier 14837 pick.
- [Phase ?]: Phase 41 Plan 02: FIXTURES.md section order deviates from the plan's literal prose listing (evidence/methodology tables moved before the final Fixture Set table) to satisfy a mechanical conflict between the plan's own gate-2 and gate-3 verify commands; no content or scope change.
- [Phase ?]: Phase 41 Plan 03: Operator confirmed the four-fixture set as proposed (confirm-as-proposed) — complexity fixture 15169 (Baltimore & Ohio Railroad Co. v. United States) and state-variety targets 13015/18897/22372 — no substitutions made.
- [Phase ?]: Phase 42 Plan 01: --conversation-id joins the existing --term/--term-range mutually-exclusive group rather than a bolt-on flag, so argparse enforces exactly one of the three; the scoped path derives its own October Term from the conversation's case_id and never calls _resolve_terms.
- [Phase ?]: Phase 42 Plan 02: The fixture delete routine is a wholly separate script from api/services/admin_arguments.py::delete_argument (never imported/subclassed/patched) so that service's DRAFT-only gate stays intact for the admin UI while this offline routine targets status=pipeline corpus fixtures by design.
- [Phase ?]: Phase 42 Plan 02: --delete-case's other-argument-link check runs strictly after the fixture's own case_arguments row is deleted, so the guard correctly counts only rows belonging to a different argument before deciding to retain or delete the case row.
- [Phase ?]: Phase 42 Plan 03: Added CASES_FILENAME/CONVERSATIONS_FILENAME/SPEAKERS_FILENAME/UTTERANCES_FILENAME constants to pipeline/corpus/loader.py so the new diff script never hand-rolls a second copy of the four raw corpus filenames.
- [Phase ?]: Phase 42 Plan 03: court_tenures integrity check cross-references every is_justice=True Person by last_name before falling back to Pitfall 2's timing-anomaly explanation, correctly separating a newly-discovered Person-dedup mismatch (White/Black/Clark/Douglas) from Marshall's known timing anomaly.
- [Phase ?]: Phase 42 Plan 04: Operator disposition (D-05/D-06 batch review) approved section-hint-derive for item 1 and bench-warn-only (not bench-general) for item 2 -- side is never reassigned for Marshall's fixture row; person-identity/classification-merging work explicitly deferred to a later phase, which also governs item 8's flag-only disposition (Person-dedup mismatch: White/Black/Clark/Douglas).
- [Phase ?]: Phase 42 Plan 05 Task 1/2: Delete-then-reimport round trip re-verified all counts against Plan 01/02's recorded baseline (arguments=166, people=343, court_tenures=123, cases term_year=1966=1, fixture utterances=480) with zero divergence; Utterance.sequence ordering proven stable (0 differences, 480 rows) across the round trip; section_hint now non-null on exactly 1/480 rows because this fixture's only real raw side transition is the single PETITIONER-side turn -- no RESPONDENT-side advocate exists in the raw advocates dict since Marshall (the real SG/respondent advocate) stays BENCH per item 2's approved bench-warn-only disposition, so the transcript page will show exactly one section-jump link, not three.
- [Phase ?]: Phase 42 Plan 05 Task 2: Exactness cross-check against FIXTURES.md's independently-derived counts for conversation 15169 found zero divergence (9 advocates, 15 distinct speakers, 8 bench speakers, 479 turns, 2 transcripts). Imported ArgumentParticipant roster (17) = 15 raw distinct speakers minus the <INAUDIBLE> unattributed sentinel, plus 2 advocates (Hugh B. Cox, Joseph Auerbach) listed in conversations.json's advocates dict but who never speak a turn -- correct behavior, not a defect. No backfill occurred: 163 pre-existing convokit_import pipeline_runs all date to 2026-07-10, none created during this phase.
- [Phase ?]: Phase 43 Plan 01: environment: str given no default, placed directly after admin_token in Settings (D-02); DEVTOOL-01/02 intentionally NOT marked complete in REQUIREMENTS.md — both require the full 4-fixture reseed and frontend gate, delivered in later plans of this phase.
- [Phase ?]: Phase 43 Plan 01: FastAPI 0.139.2 (installed) wraps include_router() results in _IncludedRouter objects with no .path attribute, breaking the flat app.routes walk RESEARCH.md's code examples assumed; fixed via a version-tolerant _all_route_paths() helper in tests/test_admin_dev_router_gate.py.
- [Phase ?]: Phase 43 Plan 02: FIXTURE_SET extended to all four confirmed fixtures (15169/13015/18897/22372) in FIXTURES.md declaration order; reseed loop now also checks for a paired AdminJob (not just Argument) and catches run_import_convokit exceptions, re-raising as ResetIncompleteError so a partial reseed never returns a short success list.
- [Phase ?]: Phase 43 Plan 02: State-realization block drives 13015 to DRAFT via approve_job, 18897 to DRAFT-then-PUBLISHED via approve_job then publish_argument (order load-bearing, publish_argument's resolve-gate requires resolved_at non-null), and 22372's AdminJob to RUNNING via the one documented direct column write (D-04) -- D-03 is scoped to Argument.status, not AdminJob.status.
- [Phase ?]: Phase 43 Plan 02: Did NOT mark DEVTOOL-01 complete in REQUIREMENTS.md -- its text requires the operator can trigger the reset from the admin panel, which ships in Plan 43-03, not this backend-only plan. Mirrors 43-01-SUMMARY's identical decision.
- [Phase ?]: Phase 43 Plan 03: ENVIRONMENT read via $env/dynamic/private (not static-private) so the Dev Tools gate is request-time, matching D-07; DEVTOOL-01/02 intentionally NOT marked complete in REQUIREMENTS.md, deferred to Plan 43-04's live production-refusal demonstration.
- [Phase ?]: Phase 44 Plan 01: api/services/admin_arguments.py and api/routers/admin.py (touched by both Task 1 and Task 2) were edited fully before either task's commit, so their diffs were staged/committed per final per-task scope rather than git-hunk-split — no behavioral difference, documented in both commit messages and the SUMMARY.
- [Phase ?]: Phase 44 Plan 01: RESOLVE-04 intentionally left un-checked in REQUIREMENTS.md — the phase's Source Coverage Audit splits it across 44-01 (backend rename, this plan) and 44-02 (Descriptor column always renders on Bench rows); marking it complete now would misrepresent state.
- [Phase ?]: Phase 44 Plan 02: 'Change' link in Resolved As only renders when row.discrepancy is present (matches pre-Phase-44 Action column's row-actions-only-for-discrepancy-rows behavior) — avoids a dead clickable link for cleanly alias-resolved rows.
- [Phase ?]: Phase 44 Plan 02: rowMatchStates seeding now sets correcting=true/disposition=confirmed/comboQuery=candidate-name for ANY row with a non-null auto_match_id (not just auto_resolved rows), collapsing Confirm/Select/Change into a single openPersonSearch entry point per D-03/D-04.

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

Last session: 2026-08-01T18:21:46.664Z
Stopped at: Completed 44-02-PLAN.md
Resume file: None

## Operator Next Steps

- Review `.planning/ROADMAP.md` (v1.7 section) and `.planning/REQUIREMENTS.md` traceability.
- Then `/gsd-discuss-phase 41` to gather context for the fixture-selection gate.
- Phases 44 and 45 are independent of the corpus track — either can be started in parallel if you'd rather begin with the Resolve rework or the bug fixes.
