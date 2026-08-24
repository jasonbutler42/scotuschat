---
gsd_state_version: 1.0
milestone: v1.8
milestone_name: Import & Provenance Re-model
current_phase: 49
current_phase_name: Review Model
status: Phase 49 REOPENED 2026-08-24 — UAT found 4 open gaps; verification status passed -> gaps_found
stopped_at: Completed 49-10-PLAN.md (D-35 second half, G-49-3 closed)
last_updated: "2026-08-24T22:50:36.675Z"
last_activity: 2026-08-24
last_activity_desc: Executed 49-10 (shared side module, backend BENCH acceptance under RESOLVE-13, converged Speakers row) — closes G-49-3
state_head: 5ec8d1fde0cf840952e7bb197bdc6b527ac45b58
progress:
  total_phases: 5
  completed_phases: 2
  total_plans: 28
  completed_plans: 26
  percent: 40
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-18 — Phase 47 complete; corpus-first / PDF-deferred scope decision recorded)

**Core value:** Anyone can open a SCOTUS oral argument and immediately follow the conversation — the chat format makes speaker identity, turn-taking, and flow self-evident without legal background.
**Current focus:** Phase 49 — Review Model (REOPENED — gap closure)

## Current Position

Phase: 49 — Review Model (reopened for gap closure)
Last activity: 2026-08-24 — Phase 49 UAT completed (31 pass / 3 issues / 0 pending); phase reopened for gap closure

**Next action:** Wave 5 (49-10, D-35's SECOND half) is now **complete** — see `49-10-SUMMARY.md`. `app/src/lib/participantSide.ts` is the new shared bucket/label/boundary-predicate module both `ResolveCard.svelte` and the argument-detail Speakers card import from. `update_participant_side` now accepts `BENCH` under RESOLVE-13's descriptor-preservation rule; `T-15-02-BENCH` is retired **as satisfied, not weakened** (four compensating controls recorded at all citation sites — the boundary confirm, the no-fallback tenure derivation, the Missing-tenure/no-person affordance, and 49-09's published lock). The Speakers card is now ONE row template reaching all five stored side values, with a two-step boundary-crossing confirm and a three-state bench companion (closing the no-person one-way trap). **G-49-3 is closed** (`49-UAT.md` updated); D-35 recorded in `49-CONTEXT.md`. Full suite: 1123 passed (baseline 1104, clean +19, no new skips). Three human-check walks (Task 1's Resolve-card regression, Task 3's six-item convergence walk, 49-09's published-lock walk) were NOT observed this session — no browser tool available to this executor; logged to `WINDOWS.md`. **`49-11` remains** — the whole-argument published lock (D-35a), which does not touch anything 49-10 changed. Still open and NOT in any gap_ids: G-49-9a needs a visual re-check, and UAT sub-item 5.6 was never observed.

Phase 49-06 close-out notes (2026-08-23):

- Dev-only `seed_unresolved_speaker_fixture` (D-33a) ships: nulls one deterministically-selected `ArgumentParticipant.person_id` (preferring a participant whose `side` is already `UNKNOWN`, traced against the real consumer code rather than the plan's literal pick) plus its matching `Utterance.person_id` rows — closing the data-layer blocker for 26-UAT Test 26 and 14-UAT Test 8, both reclassified `waived -> blocked` (not `pass`) with dated, script-verified observations.
- **D-32's live authority-conflict walkthrough performed end to end via a repeatable script against the real dev DB** — found and fixed a real, phase-central gap in the same session: `_argument_attention_predicate` had no leg for "a constituent has an open discrepancy," so an operator-edited, already-resolved participant that a lower-authority re-import disagreed with (exactly REVIEW-02/REVIEW-04's central claim) was invisible in `/admin/review`. Fixed, tested, verified by re-running the same script.
- Corrected `49-RESEARCH.md` Pitfall 4's false premise ("no live corpus path can produce an unresolved speaker") — verified false against the live dev DB (argument 1788 had 11 `person_id IS NULL` rows from a job parked pre-resolve) before this plan started; not restated anywhere in the seeder's code/docstrings.
- The frontend `readonlyMode` split (flagged and deferred by both 49-04 and 49-05) is closed: `resolveCardReadonly` (`status === 'published'`) / `metadataReadonly` (unchanged).
- All five REVIEW-0X requirements now `Complete` in REQUIREMENTS.md.
- Full suite: **1414 passed, 5 xfailed, 0 failed** (up from 1403 at phase start). Confirmed in a fully isolated run — an earlier concurrent run (this plan's own dev-DB scripts running alongside a background pytest process) produced 2 spurious `DeadlockDetectedError` failures, an environment artifact (TEST_DATABASE_URL and DATABASE_URL resolve to the same physical database in this sandbox), not a regression.
- `.planning/WINDOWS.md` gained 9 entries this plan (2 deviations found+fixed, 1 corrected-premise deviation, 8 unrun-verify browser items covering the whole phase).

Phase 49-05 close-out notes (2026-08-23):

- Full `/admin/review` screen shipped: Arguments|People tabs, the trust-tier × review-state × status filter set with a fully specified server-side sort (published-degraded first, tier rank, argued_date ASC NULLS LAST, Argument.id ASC tie-break — never created_at), expandable argument rows with discrepancy detail and the fixed-order Confirm/Confirm-as-unattributable/Edit/Re-flag action row, and the zero-constituent blockers fallback.
- Dashboard COUNT (`get_review_queue_stats`/`GET /api/admin/review/stats`) shares its inclusion predicate with the list queries by construction (`_argument_attention_predicate`/`_person_attention_predicate`), so the card and the screen can never disagree. AdminSubNav gained a Review link; the dashboard grid widened to 5 columns with a fifth StatCard.
- 27 new tests (11 query-behavior + 2 backstop in `test_admin_review_service.py`, 14 in new `test_phase49_review_ui_contract.py`). Full suite: 1403 passed, 5 xfailed, 0 failed (up from 1376/5/0).
- **Open for a human:** the Task 2 seven-item browser `<human-check>` walkthrough was not completed — same `.env`-credential-access constraint as 49-01/49-03. See `49-05-SUMMARY.md` coverage D4/D5.
- Person's provenance-note format deviates from the plan's literal `"{Source} · {method}"` spec (Person has no `method` field anywhere in `provenance_metadata`) — implemented as `"{Source} · {confidence}"` instead; documented in 49-05-SUMMARY.md Deviations.
- The frontend `readonlyMode` split (flagged by 49-04) remains open — not this plan's scope; left for 49-06 or a follow-up.
- REVIEW-03/REVIEW-04 remain `Pending` — both shared with 49-06 (not yet complete); shared-ID gate correctly held both back.

Phase 49-04 close-out notes (2026-08-23):

- Authority ladder (`api/domain/authority.py`) + the ONE gated writer (`api/services/admin_review.py`) shipped and exhaustively tested; all three named writers (`update_participant_side`, `update_resolve_row_for_job`, `update_person`) delegate — no ungated write path to `argument_participants`/`people` value columns survives.
- Fixed the D-18 regression deferred at plan 49-02 (`WINDOWS.md` #11, now marked `fixed`): `resolve_job`/`update_resolve_row_for_job` backfill `ArgumentParticipant.source`/`.method` from the job's parse-step `ImportRun` when never stamped. Full suite: 1376 passed, 5 xfailed, 0 failed (up from 1252/2 failed/5 xfailed baseline).
- REVIEW-02 and REVIEW-04 remain `Pending` in REQUIREMENTS.md — both shared with 49-05/49-06 (not yet complete); shared-ID gate correctly held both back.
- Participant editability widened to every unpublished state (candidate/draft/unpublished) — backend/API complete; the frontend `readonlyMode` flag at `app/src/routes/admin/pipeline/[job_id]/+page.server.ts:294` deliberately NOT widened (conflates Resolve-card editability with an unrelated ArgumentDetailsCard metadata form) — left for 49-05 or a follow-up. Folded todo `2026-08-21-widen-participant-editability-to-all-unpublished-states.md` stays in `pending/` (backend half done, frontend half open).

Phase 48 close-out notes (2026-08-21):

- All five requirements (TRUST-01 through TRUST-05) traced to named, green, automated checks in
  `48-EVIDENCE.md`'s requirement-traceability table, plus the carried D-22 cascade-defect fix and
  the D-23 public-leak-ban contract.

- Two new open items carried forward as standalone todos (not folded into Phase 48's own scope):
  `.planning/todos/pending/2026-08-20-reset-to-fixture-stale-created-at-timestamps.md` (the
  underlying stale-value root cause behind the display-ordering bug this plan fixed — dev-only,
  `reset_to_fixture`'s session/transaction reuse) and
  `.planning/todos/pending/2026-08-21-widen-participant-editability-to-all-unpublished-states.md`
  (operator-requested widening of Resolve-card editability scope, deliberately deferred).

- 14-UAT Test 8 and 26-UAT Test 26 remain open (see Deferred Items below) — Phase 48's Finding 1
  (48-EVIDENCE.md) shows the reason D-21 gave for not closing them may not fully hold; worth a look
  before assuming new fixture work is required.

- Three of Phase 48's defects were found by **operator browser testing**, not the automated suite
  (silent list-page 422 swallow, unpublish/public-visibility across three read paths, shared-`form`
  error-routing bug on the detail page — all in plan 48-10) — the suite grew from 1114 to 1209 tests
  across the phase and passed clean over all three fixes.

- Test suite: **1209 passed, 5 xfailed, 0 failed, 0 skipped** (baseline at Phase 48 start was 1049;
  the 5 xfailed are the never-implemented Phase 31 stubs, tracked below, unchanged).

Progress: [████░░░░░░] 40% (2 of 5 v1.8 phases complete)

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
| Phase 48 P01 | 15min | 3 tasks | 7 files |
| Phase 48 P02 | 20min | 2 tasks | 3 files |
| Phase 48 P03 | ~35min | 2 tasks | 2 files |
| Phase 48 P04 | ~50min | 3 tasks | 13 files |
| Phase 48 P05 | ~50min | 3 tasks | 7 files |
| Phase 48 P06 | ~40min | 2 tasks | 3 files |
| Phase 48 P07 | ~45min | 3 tasks | 6 files |
| Phase 48 P08 | ~35min | 3 tasks | 3 files |
| Phase 48 P10 | ~2h across 3 sessions | 4 tasks | 18 files |
| Phase 49-review-model P01 | 45min | 2 tasks | 14 files |
| Phase 49-review-model P02 | 2h | 3 tasks | 20 files |
| Phase 49-review-model P03 | 25min | 3 tasks | 6 files |
| Phase 49-review-model P04 | 100min | 3 tasks | 15 files |
| Phase 49-review-model P05 | 50min | 3 tasks | 10 files |
| Phase 49-review-model P06 | ~100min | 3 tasks | 15 files |
| Phase 49 P07 | 45min | 2 tasks | 4 files |
| Phase 49-review-model P08 | ~55min | 3 tasks | 5 files |
| Phase 49 P09 | 1h 5m | 3 tasks | 6 files |

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
- [Phase ?]: derive_tier rule 3 (operator+manual -> VERIFIED) is a flagged planner assumption pending operator confirmation at /gsd-verify-work
- [Phase ?]: Task 2 corrected the plan's erroneous third fail-closed test case to match derive_tier's actual, locked precedence semantics (unrecognised review_state alone does not override an otherwise-trusted source/method pair)
- [Phase ?]: Phase 48 Plan 02: cascade regression tests use try/finally cleanup so a failed assertion mid-test still leaves the shared scotus_test DB clean for the row-count tripwire
- [Phase ?]: Phase 48 Plan 02: kept test_delete_argument_returns_false_for_pipeline as the retired-enum-value fixture and added a distinct test_delete_argument_still_refuses_candidate rather than repurposing it
- [Phase ?]: Phase 48 Plan 03: left the admin-contract false-green guard failing loudly (not xfail) since it resolves automatically once 48-07 lands trust_tier on ArgumentDetail (D-20) -- recorded in WINDOWS.md as kind unmet-truth
- [Phase ?]: Phase 48 Plan 03: corrected the plan's /api/-prefixed endpoint paths to the actual mounted public routes (/cases, /arguments/{id}/..., /people/{id}) -- only the admin router carries an /api/admin prefix
- [Phase ?]: Phase 48 Plan 04: Rule 3 fix flipped pipeline/commands/import_convokit.py's birth-write status kwarg from PIPELINE to CANDIDATE ahead of plan 48-05's own scheduled edit, to keep this plan's guard swap internally consistent; recorded in WINDOWS.md (kind=deviation) so 48-05 finds this line already done
- [Phase ?]: Phase 48 Plan 04: renamed test_approve_job_accepts_freshly_created_argument_and_rejects_second_call to include 'candidate' so the plan's own -k filter matches all three vocabulary-block tests it names
- [Phase ?]: Phase 48 Plan 05: import_convokit.py's birth-write status kwarg was already flipped to CANDIDATE by plan 48-04's Rule 3 fix; confirmed already-done and WINDOWS.md entry 7 marked fixed
- [Phase ?]: Phase 48 Plan 05: fixed a stale test assumption in api/tests/test_admin_dev_routes.py (test_reset_writes_status_log_rows) that asserted zero status-log rows for candidate arguments -- D-03's birth-log write now produces exactly one row for those arguments, as CONTEXT.md predicted
- [Phase ?]: Phase 48 Plan 06: test file bootstraps AsyncSessionLocal via a module-local FastAPI-lifespan fixture (mirroring api/tests/conftest.py::_api_lifespan) to reuse plan 48-01's _seed_argument/_teardown_argument helper unmodified
- [Phase ?]: Phase 48 Plan 06: added a function-scoped, genuinely committed TRUNCATE fixture (mirroring pipeline/tests/conftest.py's _reset_test_db safety guard) since clean_db's rollback-based truncation is invisible to recompute-trust's separate pipeline.db.get_session() engine
- [Phase ?]: Phase 48 Plan 07: adapted 3 pre-existing zero-constituent publish tests in test_admin_arguments_service.py to pass an override_reason since floor_tier's zero-constituent base case now hits the new UNCERTAIN gate by construction
- [Phase ?]: Phase 48 Plan 07: blank-reason and pre-existing publish ValueErrors share one except ValueError router handler distinguished by inspecting str(exc), since Python cannot dispatch two handlers on the same exception class
- [Phase ?]: Phase 48 Plan 08: reused the static-source-contract shape (test_phase45_popover_boxmodel_contract.py / test_phase39_popover_ui_contract.py) for the publish-override UI contract, since this repo has no frontend test framework and node is not guaranteed on PATH for every pytest invocation
- [Phase ?]: Phase 48 Plan 10: found and fixed a real defect at the Task 4 checkpoint — the detail page's Status card never rendered publish/unpublish errors (form?.error only rendered in the unrelated case-metadata card); tagged fail() payloads with source and widened the Status-card guard
- [Phase ?]: Phase 48 Plan 10: unpublish-error rendering fix accepted on static contract test alone, not observed live (failure path requires the backend call itself to fail, unreachable from any UI state)
- [Phase ?]: Phase 48 Plan 10: WINDOWS.md entry #8 (D-14 non-overridable gate, unrun-verify) marked fixed -- the deferred live check is what surfaced the checkpoint-found defect, not a false alarm
- [Phase ?]: Phase 48 Plan 09: found and fixed a Status History display-ordering bug via live evidence-gathering -- get_argument_detail's argument_status_log query now orders by id ASC only, not created_at first, since PostgreSQL now() reflects transaction-start time not per-statement time
- [Phase ?]: Phase 48 Plan 09: derive_tier rule 3 (operator+manual -> VERIFIED) confirmed by the operator on 2026-08-21, closing plan 48-01's flagged assumption; api/domain/trust.py docstrings updated to record confirmation, logic unchanged
- [Phase ?]: Phase 48 Plan 09: two corpus fixtures (15169, 22372) read trust_tier=uncertain not trusted after reseed -- traced to ConvoKit's own unattributed-speaker sentinel rows, not a Phase 48 defect; derive_tier is correct and the plan's must-have assumption was wrong. Accepted by operator as an open item
- [Phase ?]: Phase 48 Plan 09: operator requested widening Resolve-card editability from CANDIDATE-only to {candidate, draft, unpublished} (published stays read-only) -- recorded as a new open item and standalone todo, deliberately NOT implemented (design-scope change, not a bug)
- [Phase 49]: 49-02 checkpoint decision (human, resolved): migration 0029's downgrade() is clean-reverse — reconstructs no data from review_state/provenance_metadata, matching migration 0027's precedent.
- [Phase 49]: 49-02: fixed a pre-existing 49-01 regression (import_convokit.py ArgumentParticipant rows never stamped source/method, flooring trust tier to UNCERTAIN under D-18) — in scope, implements D-20's locked mapping. A second, analogous regression in admin_jobs.py/resolve_job was left open and documented (deferred-items.md, WINDOWS.md #11) since D-20 has no locked mapping for that path and fixing it requires a new architectural decision.
- [Phase 49]: 49-03: Status-card label fix took option 1 (relabel to 'Resolved', no schema change) per the plan's pre-made decision.
- [Phase 49]: 49-03: review_state badge on the new /admin/help page sized like the 14px status badge (not the 12px passive tier badge), since review_state is a primary operator-actionable axis per the UI-SPEC screen contract -- this page's own presentational choice, not binding on plan 49-05's real queue screen.
- [Phase 49]: 49-03: could not complete the plan's live-browser human-check walkthroughs (Task 1 popover, Task 3 Help page) -- authenticating to /admin/** requires ADMIN_USERNAME/ADMIN_PASSWORD or SESSION_SECRET from .env, and this sandbox's permission policy denied reading .env. Recorded as human_judgment:true in 49-03-SUMMARY.md coverage; a human should complete both walkthroughs before UAT sign-off.
- [Phase 49]: 49-04: D-18 provenance-gap fix backfills source/method from the job's parse-step ImportRun (corpus/direct), not by routing incoming writes as operator/manual authority as the environment note's prose suggested — verified against derive_tier's actual rule table (only rule 4 reaches TRUSTED, which both failing tests assert).
- [Phase 49]: 49-04: participant editability widened from CANDIDATE-only to every unpublished state (candidate/draft/unpublished); only PUBLISHED stays read-only. Backend/API complete; frontend readonlyMode flag deliberately not widened (conflates two different editability concerns) — left for 49-05.
- [Phase 49]: 49-06: 49-RESEARCH.md Pitfall 4's premise ("no live corpus path can produce an unresolved speaker") is false — verified against the live dev DB before this plan started. The dev-only seeder was built anyway, justified by its own standalone value (a deterministic, repeatable fixture), not by the false claim.
- [Phase 49]: 49-06: the seeder prefers a participant whose side is already UNKNOWN (traced against list_argument_speakers/ChatBubble.svelte's real source) over the plan's literal "first non-BENCH participant" pick, and also nulls the matching Utterance rows — both required to actually reproduce 26-UAT Test 26 and 14-UAT Test 8's states, not just an unresolved-participant row.
- [Phase 49]: 49-06: found and fixed a real gap during D-32's own live walkthrough — _argument_attention_predicate had no leg for "a constituent has an open discrepancy" (the People-tab predicate already did), so the review queue never surfaced exactly the scenario REVIEW-02/REVIEW-04 exist to prove. Fixed same-plan.
- [Phase 49]: 49-06: readonlyMode split into resolveCardReadonly (status===published) / metadataReadonly (unchanged) — closes the item 49-04/49-05 both flagged and deferred.
- [Phase 49]: 49-06: discovered TEST_DATABASE_URL and DATABASE_URL resolve to the same physical Postgres database in this sandbox — running a full-suite pytest run and a direct dev-DB verification script concurrently produced 2 spurious DeadlockDetectedError failures (confirmed as an artifact, not a regression, by re-running in isolation). Future work in this sandbox should not run both at once.
- [Phase 49]: 49-07: rename stopped at operator-facing copy; no_constituents/ReviewQueueConstituent/constituents field left unchanged (wire code + D-34 security guard)
- [Phase 49]: 49-08: closed G-49-5a's three horizontal-overflow causes (two queue tables + the previously-undiagnosed status segment group) with overflow-x: auto containers and a repeat(auto-fit, minmax(120px, 1fr)) grid track floor; the 120px floor resolves the UAT sub-item 5 vs 7 conflict without trading one for the other, proven by an executable _tracks_that_fit arithmetic gate. Structural closure only — browser visual re-confirmation remains blocked by the same denied .env credential access as 49-01/49-03/49-05.
- [Phase 49]: 49-09: published-status guard on update_participant_side placed after the pre-existing BENCH/unresolved-side input checks (not literally first), to keep a sentinel-session unit test's no-DB-touch contract intact — still runs before the participant SELECT and both authority-gate calls, satisfying D-16's no-residue requirement.
- [Phase 49]: 49-09: two new contract assertions (test_update_participant_side_still_accepts_unpublished_and_draft, test_popover_does_not_resync_side_on_every_prop_change) were green from the start of the RED phase — documented as negative-space/continuity checks, not presented as red-then-green.
- [Phase 49]: D-35 (second half): T-15-02-BENCH retired as satisfied (not weakened) — Speakers card and Resolve card converged onto one shared side/bucket module, closing G-49-3

### Roadmap Evolution

v1.6's roadmap evolution is archived in `.planning/milestones/v1.6-ROADMAP.md`; v1.7's in `.planning/milestones/v1.7-ROADMAP.md`. Cleared here at each milestone close.

2026-08-17: v1.8 roadmap created — Phases 47–51 derived from the milestone's 25 requirements (PROV-01–06, TRUST-01–05, REVIEW-01–05, IMPORT-01–05, DS-01–04). Numbering continues from v1.7's last phase (46). Coverage 25/25, no orphans, no duplicates — the five requirement categories map 1:1 onto five dependency-ordered phases (granularity `standard`, 5 phases sits in the 4–6 band; each phase carries 4–6 requirements of real scope, so no folding was warranted). Sequencing is load-bearing: PROV (47) is the keystone everything depends on and must come first; TRUST (48) depends on provenance existing; REVIEW (49) depends on trust + provenance; IMPORT (50) depends on the new schema + review model being in place; DS (51) is deliberately last so the UI reflects the corrected domain language, and it absorbs backlog 999.4/999.6/999.8. UI hints flagged on Phase 49 (new operator review queue screen) and Phase 51 (design system / component library / listing). Out of scope confirmed in REQUIREMENTS.md: public trust display, a literal separate staging table, the White/Black/Clark/Douglas person-dedup mismatch (deferred from v1.7 Phase 42), and deployment (DEPLOY-01/03).

### Pending Todos

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
- api/tests/test_admin_jobs_service.py's 2 failing tests (resolve_job/update_resolve_row_for_job never stamp ArgumentParticipant.source/method) — **RESOLVED by plan 49-04** (WINDOWS.md entry 11, status `fixed`).
- **All eight outstanding live-browser human-check items across Phase 49 (49-01, 49-03, 49-05, 49-06) are consolidated into one ordered list in `.planning/phases/49-review-model/49-EVIDENCE.md` §9** — every underlying data/API layer has been verified by script; only the actual on-screen render is unconfirmed, blocked on this sandbox denying `.env` read access for admin credentials. Each item is also recorded in `.planning/WINDOWS.md` (kind `unrun-verify`).

### Milestone-close queue (not Phase 48 blockers)

`gsd-tools audit-open` reported 6 items needing a decision before v1.8 closes as of Phase 48
close; 49-03 closed one of them (the create-person-popover todo). 5 remain: the 4 pending todos
above and the dormant SEED-001. None of them blocks Phase 49 — they are `/gsd-review-backlog` and
`/gsd-audit-milestone` material. Recorded here so the distinction is explicit rather than rediscovered
at close.

## Session Continuity

Last session: 2026-08-24T22:50:36.378Z
Stopped at: Completed 49-10-PLAN.md (D-35 second half, G-49-3 closed)
Resume file: None

## Operator Next Steps

- **Phase 49 (Review Model) is complete.** All five REVIEW-0X requirements are `Complete`. Review `.planning/phases/49-review-model/49-EVIDENCE.md` and `49-06-SUMMARY.md` at your convenience.
- **Recommended single-sitting browser pass** (see `49-EVIDENCE.md` §9 for the exact order): open `/admin`, click Reset to Fixture then Seed unresolved speaker; open the Complexity fixture's argument edit page (26-UAT Test 26); open `/admin/review` (49-01/49-05's items, D-32's visual rendering); exercise `CreatePersonPopover`/`/admin/help` (49-03's items); optionally publish the Complexity fixture to check 14-UAT Test 8's public-page rendering.
- One standalone todo remains open from Phase 48: `2026-08-20-reset-to-fixture-stale-created-at-timestamps.md` — candidate for a future plan or `/gsd-review-backlog`. (`2026-08-21-widen-participant-editability-to-all-unpublished-states.md` is now closed — see `.planning/todos/completed/`.)
- When ready, begin Phase 50 (Import Unification) with `/gsd-discuss-phase 50`.
