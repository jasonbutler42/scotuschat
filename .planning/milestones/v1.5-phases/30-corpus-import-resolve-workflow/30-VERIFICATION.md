---
phase: 30-corpus-import-resolve-workflow
verified: 2026-07-10T22:35:52Z
status: passed
score: 17/17 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 30: Corpus Import Resolve Workflow Verification Report

**Phase Goal:** Corpus-imported arguments currently land at `status=draft` with `resolved_at` permanently NULL, which means they can never pass the existing publish gate. Route them through the same AdminJob-based paused/resolve review workflow the PDF-ingest pipeline already uses, so an operator can review and fix auto-created people (missing name parts) and speaker attributions before an argument becomes publishable.
**Verified:** 2026-07-10T22:35:52Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

Merged must-haves from all 4 plans (ROADMAP.md has no separate structured Success Criteria list for this phase beyond the Goal statement — must-haves derived per Step 2b/2c from PLAN frontmatter, verified directly against source code AND the live database, not SUMMARY narrative).

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Every corpus-imported Argument is created with `status=PIPELINE` (not DRAFT) | ✓ VERIFIED | `pipeline/commands/import_convokit.py:442` sets `status=ArgumentStatusEnum.PIPELINE`. Direct DB query on the live dev DB: 0 `convokit_import`-linked arguments remain `status='draft'`; 162 are `pipeline`, 1 is `published` (post-approve). |
| 2 | Every corpus-imported Argument gets exactly one paired AdminJob (PAUSED/RESOLVE, argument_id set) in the same per-conversation transaction | ✓ VERIFIED | `import_convokit.py:539-546` inserts `AdminJob(status=PAUSED, current_step=RESOLVE, argument_id=argument.id, ...)` with no separate commit (relies on `get_session()`'s atomic context-manager commit). DB query: `SELECT a.id, COUNT(aj.id) ... HAVING COUNT(aj.id) != 1` over all 163 convokit_import arguments returns **0 rows** — exactly one AdminJob per argument, confirmed live. |
| 3 | Paired AdminJob's `discrepancies` JSONB holds one HIT-shaped 7-key dict per resolved ArgumentParticipant | ✓ VERIFIED | `_build_discrepancies()` (`import_convokit.py:333-366`) produces exactly `raw_speaker_label/normalized/candidates/auto_match_id/auto_match_name/auto_match_role/auto_resolved`. Live DB sample (job ids 323-325) confirms this exact shape with `auto_resolved: True`, `candidates: []`. |
| 4 | Re-running an already-imported term creates no duplicate AdminJob rows | ✓ VERIFIED | `pipeline/tests/test_import_convokit_adminjob.py::test_reimport_same_conversation_creates_no_additional_adminjob` — run in isolation, **passes** (4/4 tests in this file pass standalone: `python -m pytest pipeline/tests/test_import_convokit_adminjob.py -q`). Rides the pre-existing `oyez_transcript_id` early-return gate (unchanged). |
| 5 | AdminJobResponse exposes `source: Literal["pdf","corpus"] = "pdf"` | ✓ VERIFIED | `api/schemas/admin_jobs.py:70`. `AdminJobResponse.model_fields['source'].default == 'pdf'` confirmed by direct import. |
| 6 | `list_jobs()` populates `source` via `exists()` on `PipelineRun.strategy == 'convokit_import'` | ✓ VERIFIED | `api/services/admin_jobs.py:261-282` — `is_corpus_subq` exists()-subquery joined into the projection, unpacked per row, sets `job.__dict__["source"]`. |
| 7 | `get_job()` populates `source` with the same exists()-based derivation (parity, not hardcoded) | ✓ VERIFIED | `api/services/admin_jobs.py:154-163` — single-row `exists()` correlated on `job.argument_id`, sets `job.__dict__["source"]` for real (not a default, unlike `is_archived` at this path). |
| 8 | No new DB column / Alembic migration introduced | ✓ VERIFIED | `git log --oneline -- api/services/admin_jobs.py` shows only Phase 30 code commits (no new migration file); `source` is fully derived at read time from the pre-existing `PipelineRun.strategy` column. |
| 9 | Pipeline list table (`/admin/pipeline/`) shows a Source column between Status and Created | ✓ VERIFIED | `app/src/routes/admin/pipeline/+page.svelte:609-621` (header) and `:665-676` (row `<td>`) — confirmed column order Status → Source → Created → (View) by direct source read. |
| 10 | Each row renders a quiet neutral tag ('Corpus'/'PDF') driven by `job.source` | ✓ VERIFIED | `sourceLabel()`/`sourceTagStyle()` helpers (`+page.svelte:159-165`), rendered via `<span style={sourceTagStyle()}>{sourceLabel(job.source)}</span>`. |
| 11 | Tag is static/non-interactive, only pre-existing color tokens (#94a3b8/#0f1117) | ✓ VERIFIED | `sourceTagStyle()` returns a fixed inline style string using only those two pre-existing hex tokens (confirmed by source read; matches 30-REVIEW.md's independent confirmation of "no new hex value"). |
| 12 | No detail-page (ResolveCard/RunStatusCard), filter, or bulk-tooling change made | ✓ VERIFIED | `git show --stat 6574e7b4` (per 30-03-SUMMARY.md, independently cross-checked against `git log` for this phase) touches only `+page.svelte`; no other UI files modified across the phase's commit range. |
| 13 | After re-import, every term-1955 corpus argument has `status=PIPELINE` and a paired PAUSED/RESOLVE AdminJob | ✓ VERIFIED | Direct live-DB query (independent of SUMMARY narrative): 163 distinct `convokit_import` arguments; 162 `status='pipeline'`/job `paused`/`resolve`, 1 `status='published'`/job `completed`/`resolve` (post resolve→approve round-trip). |
| 14 | No term-1955 corpus argument remains in the old status=DRAFT/no-AdminJob state | ✓ VERIFIED | Direct query: `SELECT COUNT(*) ... WHERE a.status = 'draft'` over convokit_import arguments returns **0**. |
| 15 | The wipe deleted only corpus-imported rows; no PDF-ingested argument touched | ✓ VERIFIED | Direct query: 15 non-`convokit_import` arguments exist in the DB, all pre-dating this phase's work (ids ≤ 867, no `convokit_import` PipelineRun link) — none show any sign of having been touched by the scoped wipe (their own PipelineRun/status data is unrelated to the corpus predicate). |
| 16 | No committed migration/backfill script added for the wipe-and-rerun (D-02) | ✓ VERIFIED | 30-04-SUMMARY.md declares `files_modified: []`; `git log` for the phase's commit range shows no new file under `alembic/versions/` and no new script file. |
| 17 | At least one corpus argument is demonstrably resolve→approve→publish-eligible (the publish gate is reachable) | ✓ VERIFIED | Direct live-DB query: argument id 723 is `status='published'`, `resolved_at` is a real non-null timestamp, its AdminJob is `status='completed'`/`current_step='resolve'` — independently confirms the previously-unreachable publish gate (`resolved_at IS NOT NULL`) is now reachable for a corpus-imported argument. |

**Score:** 17/17 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pipeline/commands/import_convokit.py` | Modified `_import_conversation` (status flip) + new `_build_discrepancies` helper + AdminJob insert | ✓ VERIFIED | All three present, correctly placed (status at line 442, helper at 333-366, insert at 539-546, positioned after `_import_utterances` returns per 30-RESEARCH.md Pattern 3). |
| `pipeline/tests/test_import_convokit_adminjob.py` | DB-gated test asserting status/pairing/discrepancies/idempotency | ✓ VERIFIED | Exists; 4/4 tests pass when run in isolation (`python -m pytest pipeline/tests/test_import_convokit_adminjob.py -q` → `4 passed`). |
| `api/schemas/admin_jobs.py` | New `source` field | ✓ VERIFIED | Present at line 70 with correct type/default. |
| `api/services/admin_jobs.py` | `is_corpus` exists()-subquery in `list_jobs()`/`get_job()` | ✓ VERIFIED | Present at both call sites (lines 154-163, 261-282); wired to `job.__dict__["source"]` in both. |
| `api/tests/test_admin_jobs_source.py` | Asserts `source='corpus'`/`'pdf'` classification incl. duplication guard | ✓ VERIFIED | Exists; 5/5 tests pass in isolation with `DATABASE_URL` configured (`5 passed` — the SUMMARY's claim of "5 skipped" was an artifact of `DATABASE_URL` not being exported in that shell session, not a code defect; re-ran with the env var set and all 5 pass for real against the live DB). |
| `app/src/routes/admin/pipeline/+page.svelte` | `sourceLabel()`/`sourceTagStyle()` + new Source `<th>`/`<td>` | ✓ VERIFIED | Present, correctly positioned; `npx svelte-check --tsconfig ./tsconfig.json --threshold error` → `0 ERRORS`. |
| Operator runbook (30-04-PLAN.md, ad hoc, not committed) | FK-safe scoped wipe + re-run of term-1955 batch | ✓ VERIFIED | No committed script (confirmed, D-02 upheld); live-DB state independently confirms the runbook's effect (163 arguments correctly re-shaped). |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `resolved_participants` dict (advocates loop + `_import_utterances`) | `_build_discrepancies` input | `resolved = [p for p in resolved_participants.values() if p is not None]` at line 538 | ✓ WIRED | Confirmed by source read: built only after `_import_utterances` returns, so bench Justices discovered mid-stream are included. |
| `AdminJob.discrepancies` JSONB shape | `ResolveCard.svelte` Action column | Unchanged consumer, per D-05 | ✓ WIRED (by inheritance) | Shape matches `resolve.py`'s existing HIT branch exactly (7 keys); ResolveCard itself was not modified this phase (D-05 scope boundary), and the live-DB `discrepancies` sample matches the expected shape the (unmodified) consumer already renders. |
| `Argument.status == PIPELINE` | `list_resolve_rows_for_job` editable flag / `+page.server.ts` readonlyMode | Unmodified consumer functions | ✓ WIRED (by inheritance) | These gating functions were confirmed NOT modified this phase (per plan scope boundary) and already key on `ArgumentStatusEnum.PIPELINE`; the operator's own UI verification (30-04 Task 2, resume-signal "approved") independently confirmed the ResolveCard rendered editable controls (Side select / Title input) and Confirm/Change/Create-person affordances for a re-imported corpus job. |
| `PipelineRun.strategy == 'convokit_import'` | `is_corpus_subq` exists() → `job.source` | `api/services/admin_jobs.py` | ✓ WIRED | Confirmed via both source read and passing DB-gated tests (`test_admin_jobs_source.py`, 5/5 pass live). |
| `job.source` (AdminJobResponse via `+page.server.ts` passthrough) | `sourceLabel()`/`sourceTagStyle()` → rendered `<td>` | `+page.svelte` | ✓ WIRED | Confirmed by source read; no field allowlist blocks passthrough (per 30-03-SUMMARY.md, independently re-confirmed no allowlist code exists in `+page.server.ts` scope for this phase). |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `+page.svelte` Source column | `job.source` | `AdminJobResponse.source` ← `is_corpus_subq` exists() query against live `pipeline_runs`/`admin_jobs` tables | Yes | ✓ FLOWING — confirmed against the live dev DB: querying `list_jobs()`'s equivalent SQL directly returns real `is_corpus` booleans keyed off actual `PipelineRun.strategy` rows, not a static/empty fallback. |
| `_build_discrepancies` → `AdminJob.discrepancies` | `resolved_participants` values | `ArgumentParticipant` rows written earlier in the same transaction by `_resolve_and_link_participant` | Yes | ✓ FLOWING — live DB sample shows real speaker names/person_ids (e.g. "Harry F. Murphy" → person 117), not placeholder/empty JSON. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Corpus-import write path produces PIPELINE + paired AdminJob (unit-level) | `python -m pytest pipeline/tests/test_import_convokit_adminjob.py -q` | `4 passed in 2.88s` | ✓ PASS |
| `source` derivation classifies corpus vs pdf correctly, incl. duplication guard | `DATABASE_URL=<dev-db> python -m pytest api/tests/test_admin_jobs_source.py -q` | `5 passed in 2.63s` | ✓ PASS |
| No new svelte-check errors from the Source column change | `npx svelte-check --tsconfig ./tsconfig.json --threshold error` | `0 ERRORS 16 WARNINGS 10 FILES_WITH_PROBLEMS` (pre-existing warnings, no new errors) | ✓ PASS |
| Live DB: all 163 term-1955 corpus arguments correctly shaped | Direct `asyncpg`/SQLAlchemy queries against the dev DB (this verifier's own scratchpad scripts, not SUMMARY narrative) | 162 pipeline/paused/resolve, 1 published/completed/resolve, 0 remaining draft, 0 arguments with ≠1 AdminJob | ✓ PASS |
| Regression: sibling admin_jobs test files unaffected by Phase 30 changes | `DATABASE_URL=<dev-db> python -m pytest api/tests/test_admin_jobs_list.py api/tests/test_admin_jobs_service.py -q` | `2 failed, 15 passed` — **root-caused below** | ⚠️ Pre-existing, not a Phase 30 regression (see Anti-Patterns/Gaps discussion) |

**Regression root-cause note (not a Phase 30 gap):** `test_admin_jobs_service.py::test_delete_job_removes_only_admin_job_row` and `::test_approve_job_writes_one_draft_log_row` fail due to a stale-object bug in the `approve_job()`/`get_job()` interaction (`AsyncSessionLocal` is configured `expire_on_commit=False` in `api/core/database.py`, and `synchronize_session=False` bulk updates never refresh the already-identity-mapped `job` instance within the same session, so a `get_job()` re-fetch after `commit()` returns the stale cached object). **This verifier confirmed the failure is NOT caused by Phase 30**: the exact same two tests were re-run against the pre-Phase-30 baseline version of `api/services/admin_jobs.py` (commit `cd40a59a`, swapped in temporarily and restored via `git status`-confirmed clean working tree afterward) and **fail identically** — same assertion, same stale `PAUSED` value. This is a pre-existing defect unrelated to this phase's `source`-field addition, consistent with this project's documented open test-infrastructure gaps (999.17/999.19). It is out of Phase 30's scope and not treated as a gap here per this verification's explicit instructions to root-cause rather than accept SUMMARY/pytest signal at face value.

**Data hygiene note:** Running the above DB-gated test suites (which commit real rows via `AsyncSessionLocal`, not rollback-safe fixtures — the exact 999.19 backlog defect) leaked 2 additional synthetic `Argument`/`AdminJob` rows into the shared dev DB during this verification. This verifier identified and removed them via a scoped DELETE (ids 898, 900 — confirmed zero-content synthetic rows matching the documented 999.19 signature) and re-confirmed the corpus batch (163 arguments) and PDF-ingested batch (15 arguments) counts were restored to their pre-verification baseline. This is the exact "will recur on future test runs" behavior flagged in the phase context — tracked at ROADMAP.md backlog Phase 999.19, not a Phase 30 gap.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|--------------|-------------|--------------|--------|----------|
| PJOB-01 | 30-02, 30-03 | Pipeline Run status card: status badge + source file — extended this phase to include the Source (pdf/corpus) provenance tag | ✓ SATISFIED | `source` field + Source column implemented and verified above. |
| PJOB-02 | 30-01 | Run status card 3-state readiness (Not ready / Ready / Already created) | ✓ SATISFIED | Argument.status=PIPELINE is the precondition this state machine already keyed on (Phase 25); Phase 30 makes corpus arguments reach that gate for the first time — confirmed live (162 arguments now visible in the "paused" review state). |
| PJOB-14 | 30-01 | Resolve card fully editable in Not-ready/Ready states | ✓ SATISFIED | status=PIPELINE unblocks the existing editable-flag gate; operator UI checkpoint (30-04 Task 2) independently confirmed editable Side-select/Title-input controls for a re-imported corpus job. |
| PJOB-15 | 30-01 | Resolve card columns incl. Action (Confirm/Change/Create person) | ✓ SATISFIED | `_build_discrepancies()` HIT-shaped output is exactly what drives that Action column; live DB sample confirms correct shape; operator confirmed the affordances rendered (not "—"). |
| PJOB-18 | 30-01 | Person selection in resolve: side-first then typeahead | ✓ SATISFIED (unchanged consumer) | Not modified this phase (D-05); reachable now via status=PIPELINE + populated discrepancies. |
| PJOB-19 | 30-01 | New person mini-form in resolve | ✓ SATISFIED (unchanged consumer) | Same as above — reachability, not new UI, is this phase's contribution. |
| PJOB-20 | 30-01, 30-04 | "Create Argument" CTA lives in run status card | ✓ SATISFIED | Operator confirmed the full resolve→"Create Argument"→publish-eligible round trip on a re-imported corpus job (30-04 Task 2). |
| PJOB-21 | 30-01 | "Continue Resolve" action at bottom of resolve card | ✓ SATISFIED (unchanged consumer) | Reachable via the same status=PIPELINE fix; no orphaned requirement — all 8 IDs are pre-existing Phase 25 requirements explicitly reused per the phase's own "reused family — no new REQ IDs" framing, cross-checked against REQUIREMENTS.md (all 8 marked `[x]` / "Phase 25 / Complete", consistent with this being a reachability fix, not new UI). |

No orphaned requirements found — REQUIREMENTS.md's Phase mapping table lists these 8 IDs against Phase 25 (their original UI-build phase); Phase 30's PLAN frontmatter correctly reuses them as the applicable requirement family for this reachability-fix phase, per the phase's own explicit framing. No additional Phase-30-mapped IDs exist in REQUIREMENTS.md beyond these 8.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` debt markers found in any of the 7 files this phase modified (`import_convokit.py`, `test_import_convokit_adminjob.py`, `test_import_convokit_core.py`, `api/schemas/admin_jobs.py`, `api/services/admin_jobs.py`, `test_admin_jobs_source.py`, `+page.svelte`) | — | — | Grepped each file individually; only false-positive hits were a docstring's reference to ConvoKit's own "placeholder" sentinel values and an HTML `placeholder=` attribute unrelated to this phase. |

30-REVIEW.md (code review, already run this phase) found 0 critical issues and 3 warnings (WR-01: pipeline-CLI-module imported into API service layer for one constant; WR-02: `rerun_job()` has no guard against being called on a corpus-sourced job; WR-03: a same-name-duplicate-speaker edge case could theoretically produce duplicate discrepancy rows). None of these are exercised by the new tests and none block the phase goal (corpus arguments reaching the resolve/publish gate) — they are legitimate hardening follow-ups, consistent with the review's own "issues_found" (non-blocking) disposition, not gaps against this phase's must-haves.

### Human Verification Required

None. All must-haves were independently verifiable via source code inspection, direct live-database queries, and isolated test execution — no items require additional human judgment beyond what was already captured in the 30-03/30-04 human-verify checkpoints (which this verifier treats as evidence, cross-checked against independent DB queries rather than accepted at face value).

### Gaps Summary

No gaps found. All 17 merged must-haves (from the 4 plans' frontmatter, since ROADMAP.md's Phase 30 entry does not carry a separate structured Success Criteria list beyond its Goal statement) verified directly against the codebase and the live database — not merely against SUMMARY.md narrative. The three code-review warnings (WR-01/02/03) are legitimate but non-blocking hardening follow-ups tracked in 30-REVIEW.md; they do not prevent the phase goal (corpus arguments reaching the AdminJob-based paused/resolve review workflow and becoming publish-eligible) from being achieved, which this verifier independently confirmed via direct DB inspection (163/163 corpus arguments correctly shaped, 1 already resolve→approve→published as proof the gate is reachable).

The two `test_admin_jobs_service.py` failures encountered during regression-checking were root-caused to a pre-existing, unrelated `expire_on_commit`/`synchronize_session` staleness bug (reproduced identically against the pre-Phase-30 baseline) and are not attributed to this phase.

---

_Verified: 2026-07-10T22:35:52Z_
_Verifier: Claude (gsd-verifier)_
