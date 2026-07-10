---
phase: 29-historical-corpus-import
verified: 2026-07-10T15:10:00Z
status: passed
score: 14/14 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 13/14
  gaps_closed:
    - "The corpus importer imports every legitimately-importable historical oral argument without silent data loss on a per-docket collision — reargued cases and PDF-ingested-docket overlap are now imported at the next available question_number instead of colliding at session.flush() (CR-01, 29-09 gap closure)."
  gaps_remaining: []
  regressions: []
gaps: []
---

# Phase 29: Historical Corpus Import Verification Report

**Phase Goal:** Bulk-import historical oral arguments (terms 1955-2019, ~7,800 arguments) from the Cornell ConvoKit supreme-corpus dataset directly into cases/arguments/utterances/people/court_tenures, bypassing PDF download and LLM parsing for this batch. Source files: supreme-corpus/{utterances.jsonl,conversations.json,speakers.json}, a separately-located cases.jsonl (title/docket/dates/citation), and a justices tenure CSV (appointment/tenure backfill). Existing PDF ingest/parse/resolve pipeline stays for terms 2020+ and all future terms — this is a new, separate one-time bulk-import CLI command, not a replacement.

**Verified:** 2026-07-10
**Status:** passed
**Re-verification:** Yes — after gap-closure plan 29-09 (CR-01 docket/question collision fix)

## Goal Achievement

### Re-verification Summary

One gap-closure plan executed since the prior (2026-07-10T00:00Z) verification pass:

- **29-09** (fixes the prior verification's sole remaining BLOCKER, CR-01): the corpus importer's Argument-dedup was keyed only on `oyez_transcript_id`, while the real DB uniqueness constraint (`uq_arguments_source_docket_question`) is on `(source_docket, question_number)`, and every corpus-imported Argument hardcoded `question_number=1`. A reargued case or a docket already ingested via the ordinary PDF pipeline would collide at `session.flush()`, raise an `IntegrityError` caught only by a blanket `except Exception`, and be silently folded into the generic `conversations_errored` counter — indistinguishable data loss.

  **Independently reproduced fixed in this pass** (not taken on faith from 29-09-SUMMARY.md or 29-REVIEW.md): direct read of `pipeline/commands/import_convokit.py` confirms `_next_question_number(session, source_docket)` (lines 256-278) executes `select(func.max(Argument.question_number)).where(Argument.source_docket == source_docket)` and returns `1` when no row exists, else `max + 1`. `_import_conversation` (line 342-344) now calls this helper instead of hardcoding `question_number=1`, and the `Argument` flush (lines 354-373) is wrapped in `try/except IntegrityError`, which rolls back, increments a **new, distinct** `counters["docket_question_conflict"]`, prints a WARNING naming the `conversation_id`/`source_docket`, and returns early — `conversations_errored` is never touched by this path. The counter is registered in `_SUMMARY_COUNTER_KEYS` (line 747) and rendered as its own `"N docket/question conflicts."` field in `_print_summary` (line 788), so it flows through both per-term and multi-term rollup output.

  Ran the actual regression test suite myself (did not rely on the SUMMARY's reported pass count): `pytest pipeline/tests/test_import_convokit_core.py pipeline/tests/test_import_convokit_utterances.py -q` → **29 passed** (up from the prior pass's 27, consistent with 29-09 adding exactly 2 new tests). Read both new test bodies in full: `test_docket_already_at_question_number_1_imports_at_question_number_2` pre-seeds a `Case`+`Argument(question_number=1)` as if from the PDF pipeline, runs the real importer for the same docket, and asserts the corpus Argument lands at `question_number == 2` while the PDF row is untouched — a genuine assertion against real DB state, not a stub. `test_forced_collision_increments_docket_question_conflict_not_errored` monkeypatches `_next_question_number` to force a residual collision, runs the importer, and asserts (via `capsys` on the real printed summary line) `"0 conversations errored"` and `"1 docket/question conflicts"` — again a real behavioral assertion, not a mock of the code under test.

  **Confirmed fixed. CR-01 is closed.**

A fresh code review (`29-REVIEW.md`, re-run after 29-09) found **0 Critical/Blocker, 9 Warning, 4 Info**. I independently read every Warning against this phase's must-haves (ROADMAP success criteria + all 9 plans' `must_haves` frontmatter) and confirm none rises to BLOCKER level:

- **WR-07** (new, introduced by 29-09): `cases_created` is incremented at `_get_or_create_case`'s flush (before the Argument flush), so if the *subsequent* Argument flush hits the IntegrityError safety net and rolls back, a brand-new `Case` row created in the same transaction is correctly reverted in the DB, but `counters["cases_created"]` is a plain int that is never decremented — the printed summary can overreport `cases_created` by 1 in the narrow case of a brand-new docket that *also* collides at flush (e.g. a concurrent writer, the same residual scenario the safety net exists for). Independently confirmed by reading `_get_or_create_case` (lines 224-253) and the flush/rollback block (lines 354-373): `cases_created` is not touched in the `except IntegrityError` branch. This is a real, narrow counter-accuracy defect — it does **not** cause silent data loss (the DB itself ends up correct; only the printed count can drift in a rare race), and it does not violate any of 29-09's four `must_haves.truths` (which are specifically about `question_number` derivation and the `docket_question_conflict` counter, not `cases_created`). Reasonably classified as Warning, not Blocker.
- **WR-01, WR-03, WR-04, WR-05, WR-06, WR-08, WR-09**: all pre-existing (WR-01/03/04/05/06 re-affirmed unchanged, not touched by 29-09) or narrow edge cases (WR-08's mixed-turn-no-speaker stage-direction drop; WR-09's full-name-fallback identity merge) that were already weighed in the prior verification pass or are inherent to explicitly-documented design decisions (D-12: "no automated QA gate... import everything"). None contradicts an explicit `must_haves` truth, artifact, or key-link for any of the 9 plans, and none was introduced by or altered by 29-09 (confirmed via `git log`/file-touch scope: 29-09 only modified `pipeline/commands/import_convokit.py`'s question-number/counter logic and its test file).
- **WR-02**: `participants_created` is omitted from `_SUMMARY_COUNTER_KEYS`, so it never appears in `_print_summary`'s per-term OR rollup output (independently confirmed by reading `_print_summary`'s format string — the field simply isn't referenced anywhere in it, a slightly broader finding than the review's "rollup only" framing, but the same root cause). CORPUS-08's actual wording ("counts of arguments/utterances/people created... not silent") does not name `participants_created` specifically, and the counter itself is still tracked internally (not lost, just not printed). Pre-existing, unrelated to 29-09's scope. Non-blocking.

**Conclusion: no Warning is reclassified as a BLOCKER.** All 14 must-haves are now VERIFIED and the phase goal is achieved.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `Case.oyez_case_id`, `Argument.oyez_transcript_id`, `Person.oyez_speaker_id` nullable columns exist (CORPUS-02) | ✓ VERIFIED (regression check) | `alembic/versions/0017_add_oyez_external_ids.py` present; `api/models/models.py` declares matching columns; unchanged since prior verification |
| 2 | `data/corpus/` scaffolding + `python-dateutil` dependency (CORPUS-04) | ✓ VERIFIED (regression check) | `data/corpus/.gitkeep`/`.gitignore` unchanged; not touched by 29-09 |
| 3 | Streaming JSONL loader, stage-direction detector, apolitical allowlist extractors (CORPUS-05, CORPUS-06) | ✓ VERIFIED (regression check) | `pipeline/corpus/{loader,stage_directions,apolitical}.py` present, untouched by 29-09 |
| 4 | `import-justices` upgrade/dedup/idempotency (CORPUS-01, CORPUS-11) | ✓ VERIFIED (regression check) | `pipeline/commands/import_justices_csv.py` present, untouched by 29-09; not in 29-09's file list |
| 5 | `import-convokit` creates Case/Argument/CaseArgument/PipelineRun scaffolding, draft status, `term_year` from `cases.jsonl`, apolitical stripping (CORPUS-03) | ✓ VERIFIED | Creation path correct and tested (29/29 pipeline import tests pass, independently re-run); read directly and confirmed unchanged except for the `question_number` derivation (Task 1) |
| 6 | Bench/advocate speaker resolution, `SideEnum` mapping, idempotent `ArgumentParticipant` creation (CORPUS-05) | ✓ VERIFIED (regression check) | `test_import_convokit_core.py` suite passes in full (independently re-run) |
| 7 | Each ConvoKit turn becomes one `Utterance` row, `\n` preserved verbatim (CORPUS-07) | ✓ VERIFIED (regression check) | `test_import_convokit_utterances.py` suite passes in full, including the 29-08 end-to-end readability test |
| 8 | Stage-direction detection + row-splitting (CORPUS-06) | ✓ VERIFIED (regression check) | Same suite, unchanged tests still pass |
| 9 | Per-batch summary report (CORPUS-08) | ✓ VERIFIED — caveat resolved | `docket_question_conflict` is now its own distinct, clearly-labeled field in `_print_summary` (line 788), independently confirmed by direct read and by the new test's `capsys`-captured assertion `"1 docket/question conflicts"` alongside `"0 conversations errored"` — the prior pass's caveat about `conversations_errored` conflating a docket collision with unrelated errors no longer applies |
| 10 | `/attributions` page, TopNav link, README credits (CORPUS-09) | ✓ VERIFIED (regression check) | `app/src/routes/attributions/+page.svelte` present, untouched by 29-09 |
| 11 | Per-argument attribution note, corpus-sourced only, server-gated (CORPUS-10) | ✓ VERIFIED (regression check) | `+page.server.ts`/`+page.svelte` gating logic untouched by 29-09; unaffected by this pass's changes |
| 12 | No regressions to pre-existing pipeline/API test suites | ✓ VERIFIED | Full `pipeline/tests/` re-run this session: **133 passed, 14 failed** — the same 14 pre-existing, phase-29-unrelated failures documented in every prior verification pass (`test_ingest`/`test_parse`/`test_pipeline_run`/`test_resolve`/`test_seed_aliases`, the known FastAPI/session-factory bug family); 2 additional passes vs. the prior 131 reflect 29-09's 2 new tests exactly |
| 13 | A corpus-imported draft Argument can be viewed (`GET /arguments/{id}/utterances` returns 200) regardless of `argued_date`, AND its utterances are non-empty/retrievable | ✓ VERIFIED (regression check) | Unchanged since the prior pass (29-07/29-08 fixes); not touched by 29-09; `test_utterances_readable_via_arguments_service_after_import` still passes as part of the 29/29 run |
| 14 | The corpus importer imports every legitimately-importable historical argument without silent per-docket-collision data loss (reargued cases; dockets already PDF-ingested) (CR-01) | ✓ **VERIFIED — gap closed** | `_next_question_number` (lines 256-278) derives `question_number` from `select(func.max(Argument.question_number)).where(Argument.source_docket == source_docket)`, aligning the write path with the real `(source_docket, question_number)` DB constraint; residual collisions are caught via `except IntegrityError`, rolled back, and counted in the new distinct `docket_question_conflict` counter. Independently re-derived from direct code read (not from 29-09-SUMMARY.md's claims) and confirmed by running (not merely reading) both new regression tests, which passed against a real test database. |

**Score:** 14/14 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pipeline/commands/import_convokit.py` — `_next_question_number` helper | Derives next `question_number` per docket from `(source_docket, question_number)` | ✓ VERIFIED | Confirmed at lines 256-278; `python -m py_compile pipeline/commands/import_convokit.py` exits 0 |
| `pipeline/commands/import_convokit.py` — `docket_question_conflict` counter | Distinct from `conversations_errored`, registered in `_SUMMARY_COUNTER_KEYS`, printed in `_print_summary` | ✓ VERIFIED | Confirmed at lines 747, 364-365, 788; `grep -c docket_question_conflict` = 6 occurrences across definition/increment/summary/tests |
| `pipeline/commands/import_convokit.py` — `IntegrityError` handling around Argument flush | Catch, rollback, count distinctly, return early | ✓ VERIFIED | Confirmed at lines 354-373; `from sqlalchemy.exc import IntegrityError` present at line 73 |
| `pipeline/tests/test_import_convokit_core.py` — reargued/PDF-overlap regression tests | Prove no silent drop on collision | ✓ VERIFIED | Two new tests (lines 684, 745) read in full and **executed directly by this verification pass** — both pass against a real test DB, not skipped |
| All artifacts verified in the prior pass (loader/stage_directions/apolitical/import_justices_csv/attributions page/schema Optional fixes/PipelineRun.step) | Unchanged | ✓ VERIFIED (regression) | Confirmed present; none touched by 29-09's file list (`pipeline/commands/import_convokit.py` + its test file only) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `import_convokit.py`'s Argument-dedup/derivation | `arguments` table's real uniqueness constraint (`uq_arguments_source_docket_question`) | `_next_question_number`'s `select(func.max(...)).where(source_docket == ...)` query, matching `(source_docket, question_number)` | ✓ **WIRED — gap closed** | Dedup key and DB uniqueness contract are now aligned; confirmed by direct read of both `import_convokit.py:256-278` and `api/models/models.py:207-216` (unmodified, read-only reference per plan constraint) |
| `docket_question_conflict` counter | `_print_summary` output (CORPUS-08 visibility) | `_SUMMARY_COUNTER_KEYS` tuple → `c.get('docket_question_conflict', 0)` in the format string | ✓ WIRED | Confirmed at lines 747 and 788; proven end-to-end by the executed `test_forced_collision_increments_docket_question_conflict_not_errored`, which captures and asserts the actual printed line |
| `import_convokit.py`'s `PipelineRun.step` write | `api/services/arguments.py`'s `step == "parse"` filter | string literal match | ✓ WIRED (regression) | Unchanged since 29-08; confirmed at line 396 |
| `+page.server.ts` | `GET /arguments/{id}/utterances` | `fetch` + `is_corpus_sourced` derivation | ✓ WIRED (regression) | Unchanged; unaffected by 29-09 |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| CORPUS-01 | 29-03 | Bulk-import historical justices, dedup/upgrade, elevated dual-tenure | ✓ SATISFIED | Unchanged since prior pass; not touched by 29-09 |
| CORPUS-02 | 29-01 | Migration adding 3 nullable oyez_* columns | ✓ SATISFIED | Unchanged |
| CORPUS-03 | 29-04/29-05/29-09 | `import-convokit` CLI: batched, resumable, draft status, lead-docket-only, reliable per-docket dedup | ✓ SATISFIED — caveat resolved | Creation/draft/lead-docket-only paths correct and tested; the CR-01 collision defect that broke "resumable/idempotent" (D-08) for reargued/PDF-overlap dockets is now closed by 29-09 |
| CORPUS-04 | 29-01 | Source-file handling, `data/corpus/`, `python-dateutil` | ✓ SATISFIED | Unchanged |
| CORPUS-05 | 29-02/29-04 | Speaker identity resolution, apolitical stripping | ✓ SATISFIED | Unchanged; not touched by 29-09 |
| CORPUS-06 | 29-02/29-05 | Stage-direction detection + row-splitting | ✓ SATISFIED | Unchanged |
| CORPUS-07 | 29-05 | Multi-sentence utterance storage, `\n` preserved | ✓ SATISFIED | Unchanged; proven end-to-end readable (29-08) |
| CORPUS-08 | 29-05/29-09 | Per-batch summary report, operator-visible counts including docket/question conflicts | ✓ SATISFIED — caveat resolved | Summary now surfaces `docket_question_conflict` as its own distinct field, closing the prior pass's caveat that a collision was indistinguishable from a generic error |
| CORPUS-09 | 29-06 | Attributions/License static page | ✓ SATISFIED | Unchanged |
| CORPUS-10 | 29-06 | Per-argument attribution note, corpus-sourced only | ✓ SATISFIED | Unchanged |
| CORPUS-11 | 29-03 | Roadmap bookkeeping (999.10 superseded) | ✓ SATISFIED | ROADMAP.md line 434 confirms `SUPERSEDED` |

No orphaned requirements — all 11 `CORPUS-*` IDs are declared across the plans' `requirements` frontmatter (29-09 correctly re-declares `CORPUS-03`/`CORPUS-08` for its fix) and are addressed by actual artifacts, verified directly against `.planning/REQUIREMENTS.md` (all 11 marked `[x]` / `Complete`).

### Anti-Patterns Found

No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers found in `pipeline/commands/import_convokit.py` or `pipeline/tests/test_import_convokit_core.py` (the two files 29-09 touched; checked directly). The 9 Warnings and 4 Info items from `29-REVIEW.md` are real, independently-confirmed findings but none is a Blocker against this phase's must-haves (see Re-verification Summary above for the item-by-item disposition). Recommend these be captured for a future hardening/backlog phase rather than blocking Phase 29's completion:

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `pipeline/commands/import_convokit.py` | 224-253, 354-373 | `cases_created` counter not reverted on the CR-01 safety-net rollback (WR-07, new, narrow race-condition edge case) | ⚠️ Warning | Summary can overreport `cases_created` by 1 in the rare case of a brand-new docket that also collides at flush; no DB-level data loss |
| `pipeline/commands/import_convokit.py` | 736, 763-789 | `participants_created` never printed in `_print_summary` (WR-02, pre-existing) | ⚠️ Warning | Tracked internally but not surfaced to the operator; CORPUS-08's specific named counts (arguments/utterances/people) are unaffected |
| `pipeline/commands/import_convokit.py` | 658-687 | Mixed spoken/stage-direction turn with unresolvable speaker drops the stage-direction row too (WR-08, new, narrow edge case) | ⚠️ Warning | Narrow data-completeness gap for stage-direction annotations only, not spoken utterances |
| `pipeline/commands/import_convokit.py` | 471-485 | Exact `full_name` fallback match can merge two different historical people (WR-09, new) | ⚠️ Warning | Inherent to the documented D-11/D-12 design (full_name fallback, no automated QA gate); operator-auditable via draft status |
| `pipeline/corpus/stage_directions.py` | 48 | Mismatched bracket/paren pairs accepted (WR-01, pre-existing) | ⚠️ Warning | Narrow misclassification edge case |
| `alembic/versions/0017_add_oyez_external_ids.py` | 34-58 | No DB-level `UNIQUE` index backing `oyez_transcript_id`/`oyez_speaker_id` (WR-04, pre-existing) | ⚠️ Warning | App-level dedup only; a concurrent-writer race (single-operator CLI tool, low likelihood) could theoretically duplicate |
| `pipeline/corpus/loader.py` | 40, 52, 69, 85 | No per-line JSON error handling (WR-05, pre-existing) | ⚠️ Warning | A single malformed line would abort the whole batch; real corpus import has not yet run against the live ~900MB files |
| `pipeline/commands/import_justices_csv.py` | 102-107, 141-230 | No error handling in CSV parse/per-row loop (WR-03, pre-existing) | ⚠️ Warning | One bad row aborts the whole justices-import run |
| `pipeline/commands/import_convokit.py` | 661-687 | Non-justice speakers not in `advocates` dict silently resolve to `SideEnum.UNKNOWN` with no counter (WR-06, pre-existing) | ⚠️ Warning | Consistent with D-12's "no automated QA gate, import everything" design |

### Scope Note: Real Corpus Import Has Not Run

Unchanged from every prior verification pass: `data/corpus/` still contains only `.gitkeep`/`.gitignore` — no operator has run `import-justices` or `import-convokit` against the real ~900MB corpus files. All findings in this pass (including CR-01's fix) were independently verified via direct code reads, `grep`, `py_compile`, and executing the real regression test suite against a real test database — not via a live production-scale import.

### Human Verification Required

None. All findings in this pass were independently reproduced via direct code reads and by actually executing (not merely reading about) the pipeline test suite (133 passed/14 pre-existing-unrelated-failed) and the two new CR-01 regression tests (both passed against a live test DB). The two `checkpoint:human-verify` gates in this phase (29-01 Task 1 package-legitimacy gate; 29-06 Task 4 visual verification) were already completed during phase execution and are unaffected by 29-09's changes (which touched only `pipeline/commands/import_convokit.py` and its test file).

### Gaps Summary

None. The sole remaining BLOCKER from the prior verification pass (CR-01: docket/question collision silently dropping data) is closed by 29-09, independently reproduced and confirmed in this pass by direct code reading and by executing the regression test suite. All 14 must-haves across all 9 plans are VERIFIED. The fresh code review's 9 Warnings and 4 Info items are real but non-blocking — none contradicts an explicit must-have, and none was left unaddressed by design intent. Phase 29's goal — bulk-importing historical oral arguments from the ConvoKit corpus into cases/arguments/utterances/people/court_tenures without silent data loss, while leaving the PDF pipeline untouched for 2020+ — is achieved.

---

_Verified: 2026-07-10_
_Verifier: Claude (gsd-verifier)_
