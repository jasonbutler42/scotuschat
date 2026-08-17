---
gsd_state_version: 1.0
milestone: v1.8
milestone_name: Import & Provenance Re-model
current_phase: 47
current_phase_name: Provenance Foundation
status: planning
stopped_at: Phase 47 context gathered
last_updated: "2026-08-17T20:14:51.404Z"
last_activity: 2026-08-17
last_activity_desc: v1.8 roadmap created (Phases 47–51 derived from 25 requirements)
progress:
  total_phases: 5
  completed_phases: 0
  total_plans: 6
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-15 after v1.7 milestone completed and archived)

**Core value:** Anyone can open a SCOTUS oral argument and immediately follow the conversation — the chat format makes speaker identity, turn-taking, and flow self-evident without legal background.
**Current focus:** Phase 47 — Provenance Foundation (first of 5 in v1.8)

## Current Position

Phase: 47 of 51 (Provenance Foundation) — first of 5 phases in v1.8
Plan: — (roadmap created; phase not yet planned)
Status: Ready to plan Phase 47
Last activity: 2026-08-17 — v1.8 roadmap created (Phases 47–51 derived from 25 requirements)

Progress: [░░░░░░░░░░] 0%

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
| backlog | Phases 999.2–999.8 | 999.4/999.6/999.8 absorbed into v1.8 Phase 51 (DS-02/04/03); rest remain backlog candidates for `/gsd-review-backlog` | 2026-07-12 |
| verification | 01/03/04-VERIFICATION.md | human_needed (stale — human UAT completed per commits) | 2026-06-15 |
| verification | 11-VERIFICATION.md | human_needed (v1.2 carry-over — Argument Metadata Editing human UAT never formally closed) | 2026-06-29 |
| context_question | Phase 999.2 (999.2-CONTEXT.md, 3 open questions) | not started | 2026-07-12 |

Acknowledged and deferred at v1.7 close on 2026-08-15 (all pre-existing backlog unrelated to what v1.7 shipped — no gaps in v1.7's own delivered scope):

| Category | Item | Status |
|----------|------|--------|
| todo | 2026-08-11-create-person-popover-side-and-selection.md (ui) | pending — candidate for `/gsd-review-backlog` |
| todo | 2026-08-12-speaker-popover-frontend-duplication-cleanup.md (ui, low) | pending — candidate for `/gsd-review-backlog` |
| todo | 2026-08-12-speakers-bench-classification-silent-fallback.md (api, low) | pending — candidate for `/gsd-review-backlog` |
| todo | 2026-08-14-revisit-pre-relocation-checkout-removal.md (dev-environment, low) | pending — revisit after the relocated repo has run without incident for a period |
| seed | SEED-001-rework-resolve-table-requirements | dormant — the bulk of this seed was already absorbed into RESOLVE-01–06 (Phase 44); remaining scope, if any, is a candidate for `/gsd-review-backlog` |
| deferred_item | Phase 43/44 — 4 pre-existing `test_phase38_people_ui_contract.py` Node-subprocess path-concatenation failures (Windows/WSL path glued without separators) | not fixed — confirmed pre-existing and unrelated to both phases; not in either phase's own `files_modified` (tracked as backlog 999.10) |
| deferred_item | Phase 44 — full-suite invocation quirk (`pytest api/tests -q` skips the `tests/conftest.py` DB redirect since `tests/` is a sibling, not ancestor, path) | documented convention note — superseded in spirit by Phase 46's rootdir-conftest fix, which closes this class of invocation-shape gap going forward |

## Performance Metrics

- v1.5: 10 phases, 55 plans, 10 days (2026-07-02 → 2026-07-12)
- v1.6: 11 phases, 51 plans, 17 days (2026-07-12 → 2026-07-29)
- v1.7: 6 phases, 29 plans, 18 days (2026-07-29 → 2026-08-15)
- v1.8: 5 phases (47–51), plans TBD — roadmap created 2026-08-17

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| — | — | — | — |

v1.7 per-plan metrics cleared at this milestone boundary per the standard STATE.md reset; the underlying per-plan SUMMARY files remain in `.planning/milestones/v1.7-phases/`.

## Accumulated Context

### Decisions

Full cross-milestone decision log lives in PROJECT.md's Key Decisions table. Per-phase decisions for v1.7 (Phases 41–46) are archived in `.planning/milestones/v1.7-phases/*/`-SUMMARY.md and `.planning/milestones/v1.7-ROADMAP.md`; cleared here at milestone close per the standard STATE.md reset.

**Design basis for v1.8 (read before planning any phase):** `.planning/notes/import-architecture-diagnosis.md`, `provenance-and-trust-model.md`, `import-entity-sketch.md`.

**Carry-forward constraints that v1.8 planning must respect:**

- [Diagnosis → affects Phase 47]: This is a targeted re-model of the import/provenance layer, NOT a rewrite. The read model, people, tenures, and utterance display are stable and explicitly out of scope. Do not touch CASE, CASE_ARGUMENT, or the utterance/participant/person read shapes beyond the provenance/review fields the sketch calls out.
- [Provenance model → affects Phase 47/50]: `import_run` generalizes `pipeline_run`; the corpus path must STOP fabricating PDF-shaped `pipeline_run` artifacts. `pdf_path`/`pdf_url` are nullable and only populated for `source=pdf_pipeline`. Utterances FK to `import_run_id`, not `pipeline_run_id`.
- [Provenance model → affects Phase 48]: Every argument is born a `candidate` carrying a trust verdict; the gate is at promotion (`published_at`), NOT at row-creation. Status-based staging (candidate rows in `arguments`), NOT a separate staging table.
- [Trust model → affects Phase 48/49/50]: "Operator work is sacred" is the single most important invariant — a re-import never overwrites a human-confirmed or human-edited value. The authority ladder (operator > corpus > pdf/rule_based > pdf/llm_corrective) governs every writer; equal-or-higher-authority disagreement records a discrepancy rather than silently overwriting.
- [Trust model + apolitical constraint → affects Phase 48/49/51]: Trust tiers are operator-facing ONLY. Never surface trust/tier on the public site — it risks the apolitical framing hard constraint. Public sees published-or-not, nothing more.
- [Backfill → affects Phase 47]: Migration must preserve existing corpus + PDF data with zero loss; backfill provenance deterministically from today's `strategy` + `oyez_*` nullability per the documented old→new mapping. Alembic is the sole DDL authority — never `Base.metadata.create_all`.
- [CLAUDE.md → affects Phase 47/50]: Pipeline is offline-only (CLI, never HTTP endpoints). PG enum values can't be dropped — likely ADD `candidate` and stop using `pipeline` rather than rename.
- [Phase 29 → affects Phase 50]: The ConvoKit importer applies a positive apolitical allow-list, not a blocklist — partisan/outcome fields are dropped by design and SCDB data is never imported. Preserve this when corpus import moves to writing `import_run` directly.
- [Phase 29 CR-01 → affects Phase 50]: `question_number` is derived per-docket via `select(func.max(...))` against the real `(source_docket, question_number)` UNIQUE constraint. Any re-import/idempotency path must preserve that derivation, not hardcode `1`.
- [Phase 31 → affects every phase]: The test suite runs against `scotus_test` via `TEST_DATABASE_URL` with a rootdir `conftest.py` (Phase 46) that fails any run changing shared-dev-DB row counts. New DB-gated tests must respect this isolation.
- [Phase 44/RESOLVE-05 → affects Phase 49]: `name_needs_review`/`name_extraction_metadata` is the existing pattern REVIEW-05 must generalize into the unified `review_state` + provenance record — generalize it, do not build a parallel mechanism. Extracted-value hints use the shared `CopyableExtractedValue` component (stacked provenance mode from Phase 38).

### Roadmap Evolution

v1.6's roadmap evolution is archived in `.planning/milestones/v1.6-ROADMAP.md`; v1.7's in `.planning/milestones/v1.7-ROADMAP.md`. Cleared here at each milestone close.

2026-08-17: v1.8 roadmap created — Phases 47–51 derived from the milestone's 25 requirements (PROV-01–06, TRUST-01–05, REVIEW-01–05, IMPORT-01–05, DS-01–04). Numbering continues from v1.7's last phase (46). Coverage 25/25, no orphans, no duplicates — the five requirement categories map 1:1 onto five dependency-ordered phases (granularity `standard`, 5 phases sits in the 4–6 band; each phase carries 4–6 requirements of real scope, so no folding was warranted). Sequencing is load-bearing: PROV (47) is the keystone everything depends on and must come first; TRUST (48) depends on provenance existing; REVIEW (49) depends on trust + provenance; IMPORT (50) depends on the new schema + review model being in place; DS (51) is deliberately last so the UI reflects the corrected domain language, and it absorbs backlog 999.4/999.6/999.8. UI hints flagged on Phase 49 (new operator review queue screen) and Phase 51 (design system / component library / listing). Out of scope confirmed in REQUIREMENTS.md: public trust display, a literal separate staging table, the White/Black/Clark/Douglas person-dedup mismatch (deferred from v1.7 Phase 42), and deployment (DEPLOY-01/03).

### Pending Todos

- `2026-08-11-create-person-popover-side-and-selection.md` (ui, minor) — unassigned. Create-person popover in the Resolve card should inherit the row's current Bench/Advocate side as its default, and the newly created person should be visibly selected afterward. Found during Phase 44-09 checkpoint live-testing; deferred, not blocking. Candidate for `/gsd-review-backlog`.
- `2026-08-12-speakers-bench-classification-silent-fallback.md` (api, low) — unassigned, from Phase 45 code review.
- `2026-08-12-speaker-popover-frontend-duplication-cleanup.md` (ui, low) — unassigned, from Phase 45 code review.
- `2026-08-14-revisit-pre-relocation-checkout-removal.md` (dev-environment, low) — revisit after the relocated repo has run without incident for a period.

### Blockers/Concerns

**Directly relevant to v1.8:**

- **[affects Phase 47/50]** `api/services/admin_arguments.py::delete_argument` historically omitted `argument_status_log` from its FK cascade (found during Phase 31). Any wipe/re-import/idempotency path that deletes arguments must account for the full FK-ordered cascade or it will raise `ForeignKeyViolation`. Confirm the current cascade order before relying on it.
- **[affects Phase 47]** Run `alembic current` before assuming a migration needs applying — the dev DB was believed to be at head `0024`/`0025` (v1.7 added migration 0025 for the descriptor rename). Confirm the real head first; Alembic is the sole DDL authority for the new `import_run` schema.
- **[affects Phase 48/49]** `argument_status` is a PG enum and PG cannot drop enum values — adding `candidate` and ceasing use of `pipeline` is the likely path (per `import-entity-sketch.md` open items), not a rename. Decide `import_run` per-argument vs. a separate `import_batch` grouping at Phase 47 plan time (leaning per-argument to preserve the Utterance FK).

**Deployment blockers (v1.4, unresolved — explicitly out of v1.8 scope, carried to a later milestone):**

- `BODY_SIZE_LIMIT=10M` must be set in DO App Platform env
- `ORIGIN`, `PROTOCOL_HEADER`, `HOST_HEADER` env vars required on DO
- `admin.scotuschat.com` DNS entry must be created before smoke test

**Process concern carried from Phase 40.1 (PROJECT.md Key Decisions, ⚠️ Revisit):**

- When a fix for a previously-diagnosed issue lands via a commit outside the formal plan sequence, flip the source debug session's / verification's `status` field in that same commit. v1.6 lost a phase slot (40.1) to a stale `diagnosed` status; no structural fix shipped.

## Session Continuity

Last session: 2026-08-17T16:28:10.358Z
Stopped at: Phase 47 context gathered
Resume file: .planning/phases/47-provenance-foundation/47-CONTEXT.md

## Operator Next Steps

- Review the v1.8 roadmap draft in `.planning/ROADMAP.md` (Phases 47–51).
- When ready, plan the first phase with `/gsd-plan-phase 47`.
