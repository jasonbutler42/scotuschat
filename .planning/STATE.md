---
gsd_state_version: 1.0
milestone: v1.8
milestone_name: Import & Provenance Re-model
current_phase: 48
current_phase_name: Trust & Lifecycle
status: "Phase 47 shipped; cross-phase UAT audit closed — ready for Phase 48 discuss"
stopped_at: "Phase 47 complete and verified. Cross-phase UAT audit closed 2026-08-18 (72 items → 1 open finding, folded into Phase 48). Outstanding human UAT waived by operator. Next: /gsd-discuss-phase 48"
last_updated: "2026-08-18T23:10:00.000Z"
last_activity: 2026-08-18
progress:
  total_phases: 5
  completed_phases: 1
  total_plans: 6
  completed_plans: 6
  percent: 20
last_activity_desc: "Cross-phase UAT audit closed; human UAT waived; Phase 48 ready to discuss"
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-18 — Phase 47 complete; corpus-first / PDF-deferred scope decision recorded)

**Core value:** Anyone can open a SCOTUS oral argument and immediately follow the conversation — the chat format makes speaker identity, turn-taking, and flow self-evident without legal background.
**Current focus:** Phase 48 — Trust & Lifecycle (Phase 47 complete 2026-08-18)

## Current Position

Phase: 48 — Trust & Lifecycle
Plan: Not started
Status: Ready to discuss — no blocking loose ends
Last activity: 2026-08-18

**Next action:** `/gsd-discuss-phase 48`

Pre-flight for Phase 48, settled 2026-08-18:

- Cross-phase UAT audit closed. The audit query now returns exactly one open finding — the
  `delete_argument` / `argument_status_log` cascade defect — and it is folded into Phase 48's own
  scope (ROADMAP.md → Phase 48 → "Carried defect folded in 2026-08-18"). Nothing else from v1.0–v1.7
  is outstanding.
- All remaining human UAT is waived (see the table below). No operator testing is queued.
- Test suite is fully green: **1049 passed, 5 xfailed, 0 failed, 0 skipped**. The 5 xfailed are the
  never-implemented Phase 31 stubs, tracked below.
- **Still unverified before planning migrations:** run `alembic current` against the dev DB and
  compare to head `0026` (`0026_import_run_provenance`, Phase 47). The audit could not check this —
  it had no DB credentials. This is the pre-existing STATE.md blocker below, not a new one.

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
| verification | 01-VERIFICATION.md, 03-VERIFICATION.md | RESOLVED closed 2026-08-18 by `/gsd-audit-uat` — status flipped to `passed`; 03's five items map 1:1 onto `03-HUMAN-UAT.md` (complete, 5/5 pass) and 01's two are superseded by them | 2026-06-15 |
| verification | 04-VERIFICATION.md | CLOSED 2026-08-18 — 3 of 5 items verified against `04-UAT.md` (8/8 pass); the other 2 **WAIVED by operator, not verified**: no screen reader and no axe-core/WAVE scan has ever been run against this codebase. Recorded via the file's `overrides` block so `status: passed` never implies they were checked. **Accepted risk** on a phase whose goal is WCAG 2.1 AA — see the Blockers/Concerns entry | 2026-06-15 |
| verification | 11-VERIFICATION.md | RESOLVED closed 2026-08-18 by `/gsd-audit-uat` — status flipped to `passed`; all three items map 1:1 onto `11-UAT.md` Tests 1–3 (pass), and 11-UAT's one failed Gap was closed as BUG-01 in Phase 45 | 2026-06-29 |
| context_question | Phase 999.2 (999.2-CONTEXT.md, 3 open questions) | not started | 2026-07-12 |
| test_coverage | Phase 31 — 5 never-implemented `xfail(strict=True)` test stubs (`test_resolve_alias_hit`, `test_resolve_interactive_prompt`, `test_resolve_resumes_after_interrupt`, `test_seed_creates_justices`, `test_seed_idempotent`) | STILL OPEN — surfaced by the 2026-08-18 UAT audit as the one non-stale item in Phase 31's deferred-items.md besides the `delete_argument` cascade. All 5 bodies are `pytest.fail("not implemented")` behind `xfail(strict=True)`, so the suite reports 0 failures and the gap is invisible; they are exactly the full suite's `5 xfailed`. Real coverage work (mocked interactive `input()` flow, a resume-after-interrupt DB scenario, full seed-aliases integration), not a documentation fix | 2026-07-29 |
| human_uat | 4 UAT items the audit confirmed still testable | CLOSED 2026-08-18. **07-UAT Test 14 → pass**, verified automatically (ran `pipeline {ingest,parse,resolve} --help`; all flags present — the original blocker was an unactivated venv, never a defect). The other three **WAIVED by operator, not verified**: 07-UAT Test 13 (failed-state panel — needs a deliberately failed live run; re-test at Phase 50 with the PDF path), 26-UAT Test 26 (unresolved-advocate placeholder + Save gate — code confirmed present at `admin/arguments/[id]/+page.svelte:497,544` but never exercised in a browser; natural fit for Phase 49), 14-UAT Test 8 (needs an argument containing an unresolved speaker, which has never existed) | 2026-08-18 |

Acknowledged and deferred at v1.7 close on 2026-08-15 (all pre-existing backlog unrelated to what v1.7 shipped — no gaps in v1.7's own delivered scope):

| Category | Item | Status |
|----------|------|--------|
| todo | 2026-08-11-create-person-popover-side-and-selection.md (ui) | pending — candidate for `/gsd-review-backlog` |
| todo | 2026-08-12-speaker-popover-frontend-duplication-cleanup.md (ui, low) | pending — candidate for `/gsd-review-backlog` |
| todo | 2026-08-12-speakers-bench-classification-silent-fallback.md (api, low) | pending — candidate for `/gsd-review-backlog` |
| todo | 2026-08-14-revisit-pre-relocation-checkout-removal.md (dev-environment, low) | pending — revisit after the relocated repo has run without incident for a period |
| seed | SEED-001-rework-resolve-table-requirements | dormant — the bulk of this seed was already absorbed into RESOLVE-01–06 (Phase 44); remaining scope, if any, is a candidate for `/gsd-review-backlog` |
| deferred_item | Phase 43/44 — 4 pre-existing `test_phase38_people_ui_contract.py` Node-subprocess path-concatenation failures (Windows/WSL path glued without separators) | RESOLVED closed 2026-08-18 by `/gsd-audit-uat` — VERIFIED FIXED: 23 passed / 0 failed with `node` on PATH; the mangled `C:\workspace\...` path came from the pre-relocation Windows checkout. Backlog 999.10 removed from ROADMAP.md. **Caveat:** these 4 tests SKIP (not fail) when `node` is absent from PATH, which is the default for pytest launched outside an nvm shell — a future regression there would be invisible |
| deferred_item | Phase 44 — full-suite invocation quirk (`pytest api/tests -q` skips the `tests/conftest.py` DB redirect since `tests/` is a sibling, not ancestor, path) | RESOLVED closed 2026-08-18 by `/gsd-audit-uat` — fully superseded, not just in spirit: Phase 46 moved `conftest.py` to the pytest rootdir so the redirect fires for every invocation shape, locked in by `tests/test_pytest_isolation_invocation_shapes.py` |

Cross-phase UAT audit — 2026-08-18 (`/gsd-audit-uat`):

Scanned all 18 UAT / VERIFICATION / deferred-items files across 15 phases (v1.0–v1.7) and
cross-referenced every item against current source plus two full test-suite runs. **72 outstanding
items → 14.** Every closure carries its evidence in the file it closes; the consolidated record is
`.planning/notes/2026-08-18-uat-audit-closure.md`.

- **60 of the 72 closed as stale** — 38 deferred-item bullets, 13 human-verification items, 6 UAT
  gaps, 1 UAT test block, 2 parser false positives. The bulk is ~35 "pre-existing DB-gated test
  failure" deferrals across Phases 25/26/28/29/31 that Phase 31's `TEST_DATABASE_URL` isolation and
  Phase 46's rootdir `conftest.py` relocation had already fixed without anyone closing the records.
  The rest: UAT gaps closed by later phases (Phase 44's Resolve rework, Phase 25's CR-01, the
  `published_at` gate, Phase 45's BUG-01/BUG-02); human-verification items whose `status` was never
  flipped after the closing work landed elsewhere; a stale `alembic current` assertion (head is now
  0026); and two phantom items from a commented-out bullet list in 25-UAT.md that still parses as
  `## Gaps` entries.
- **12 of the originals remain open**, all genuinely so: 6 facets of the one `delete_argument`
  cascade defect (folded into Phase 48), 4 live UAT items, and Phase 04's 2 never-run accessibility
  checks. The audit query now reports **14** because the audit added two tracking bullets to that
  `delete_argument` entry (the re-confirmation and the Phase 48 pointer).
- **3 findings recorded in no existing file.** Two were fixed during the audit:
  (N-1) 4 tests in `api/tests/test_phase44_argument_role_roundtrip.py` failed in full-suite order —
  `isinstance(body.side, SideEnum)` was False because `tests/test_admin_router.py::test_api_main_imports_without_error`
  purges and re-imports every `api.*` module mid-session, so the test's fresh `SideEnum` import was a
  different class object from the one `ResolveRowUpdate` was built with (same hazard Phase 31's
  T-31-19 documents for `ImportRun`); now resolved via `model_fields["side"].annotation`.
  (N-2) all 6 live tests in `api/tests/test_published_gate.py` were silently skipping for want of
  seed data, so Phase 45's BUG-01 integration evidence was not actually executing; they now seed and
  tear down their own published/unpublished rows. (N-3) the 4 `test_phase38_people_ui_contract.py`
  node tests skip rather than fail when `node` is off PATH — carried as a caveat above.
- **Test-suite baseline after the audit's fixes:** see the run recorded in the closure note.

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
- `2026-08-18-pdf-provenance-live-fixture-verification.md` (pipeline, minor) — from Phase 47's SC-4 operator override. The `pdf_pipeline/rule_based` and `pdf_pipeline/llm_corrective` provenance legs are proven by pytest against `TEST_DATABASE_URL`, but not by a live `reset_to_fixture` re-seed, because no PDF fixture exists in the repo. Deliberately deferred with the PDF route per the corpus-first scope decision; pick up when the PDF upload path comes back (Phase 50 or later). *Was missing from this list — added 2026-08-18 during the UAT audit's pre-Phase-48 sweep, found via `gsd-tools audit-open`.*

### Blockers/Concerns

**Directly relevant to v1.8:**

- **[FOLDED INTO PHASE 48 — 2026-08-18]** `api/services/admin_arguments.py::delete_argument` still omits `argument_status_log` from its FK cascade (found during Phase 31, re-confirmed by reading current source during the 2026-08-18 UAT audit). The cascade runs Utterance → ImportRun → ArgumentParticipant → CaseArgument → NULL `AdminJob.argument_id` → Argument with no `ArgumentStatusLog` step; that FK has no `ondelete` (`api/models/models.py:507`) and `approve_job` writes an `ArgumentStatusLog(DRAFT)` row for every argument it creates (`api/services/admin_jobs.py:591`), so the Danger Zone delete on an approve-created DRAFT should raise `ForeignKeyViolation`. Still static analysis — no live repro yet. Now carried as explicit Phase 48 scope (see ROADMAP.md Phase 48, "Carried defect folded in 2026-08-18"), including correcting the wrong comment at `scripts/delete_fixture_argument.py:25`. Phases 47/50's re-import and idempotency paths depend on this cascade being correct.
- **[affects Phase 47]** Run `alembic current` before assuming a migration needs applying — the dev DB was believed to be at head `0024`/`0025` (v1.7 added migration 0025 for the descriptor rename). Confirm the real head first; Alembic is the sole DDL authority for the new `import_run` schema.
- **[affects Phase 48/49]** `argument_status` is a PG enum and PG cannot drop enum values — adding `candidate` and ceasing use of `pipeline` is the likely path (per `import-entity-sketch.md` open items), not a rename. Decide `import_run` per-argument vs. a separate `import_batch` grouping at Phase 47 plan time (leaning per-argument to preserve the Utterance FK).

**Accepted risk from the 2026-08-18 human-UAT waiver:**

- **[affects Phase 51]** Phase 04's accessibility compliance is asserted, not measured. No assistive
  technology walkthrough and no axe-core/WAVE scan has ever been run against the argument view; the
  ARIA markup and contrast tokens were only ever checked by reading source. Waived by operator on
  2026-08-18 via `04-VERIFICATION.md`'s `overrides` block. Phases 14, 38, 39 and 45 have all changed
  the popover and argument view since, so the covered surface has drifted from the verified one. The
  cheap permanent fix is an axe-core assertion inside a browser test rather than a human checklist —
  worth folding into Phase 51 when it reworks this UI.
- **[affects Phase 49/50]** Three UAT behaviours are implemented but have never been observed:
  the failed-run error panel (`FailedStepGuidance.svelte`), the unresolved-advocate role placeholder
  and per-row Save gate on the argument editor, and the non-interactive avatar for an unresolved
  utterance. Each is a plausible free rider on Phase 49's review work or Phase 50's import rework.

**Deployment blockers (v1.4, unresolved — explicitly out of v1.8 scope, carried to a later milestone):**

- `BODY_SIZE_LIMIT=10M` must be set in DO App Platform env
- `ORIGIN`, `PROTOCOL_HEADER`, `HOST_HEADER` env vars required on DO
- `admin.scotuschat.com` DNS entry must be created before smoke test

**Process concern carried from Phase 40.1 (PROJECT.md Key Decisions, ⚠️ Revisit):**

- When a fix for a previously-diagnosed issue lands via a commit outside the formal plan sequence, flip the source debug session's / verification's `status` field in that same commit. v1.6 lost a phase slot (40.1) to a stale `diagnosed` status; no structural fix shipped.

### Milestone-close queue (not Phase 48 blockers)

`gsd-tools audit-open` reports 6 items needing a decision before v1.8 closes: the 5 pending todos
above and the dormant SEED-001. None of them blocks Phase 48 — they are `/gsd-review-backlog` and
`/gsd-audit-milestone` material. Recorded here so the distinction is explicit rather than rediscovered
at close.

## Session Continuity

Last session: 2026-08-17T16:28:10.358Z
Stopped at: Phase 47 context gathered
Resume file: .planning/phases/47-provenance-foundation/47-CONTEXT.md

## Operator Next Steps

- Review the v1.8 roadmap draft in `.planning/ROADMAP.md` (Phases 47–51).
- When ready, plan the first phase with `/gsd-plan-phase 47`.
