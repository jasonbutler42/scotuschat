---
phase: 48-trust-lifecycle
plan: 05
subsystem: pipeline
tags: [sqlalchemy, postgresql, pytest, trust-tier, argument-status, offline-pipeline]

requires:
  - phase: 48-trust-lifecycle
    plan: 01
    provides: "ArgumentStatusEnum.CANDIDATE, Argument.trust_tier column, and the non-committing api.services.trust.recompute_argument_tier(db, argument_id) helper"
  - phase: 48-trust-lifecycle
    plan: 04
    provides: "Every admin-side PIPELINE->CANDIDATE editability guard swapped; import_convokit.py's birth-write status kwarg already flipped to CANDIDATE ahead of this plan's own scope (Rule 3 fix, recorded in WINDOWS.md entry 7)"
provides:
  - "Corpus import (import_convokit.py) writes a born-state ArgumentStatusLog row at birth and stamps trust_tier via recompute_argument_tier as the last write of _import_conversation, inside the same birth transaction"
  - "PDF ingest (ingest.py) writes a born-state ArgumentStatusLog row at birth and recomputes trust_tier inside the same get_session() block, with no explicit status kwarg on the Argument(...) construction (relies on the model default)"
  - "parse.py recomputes trust_tier on the success path only, after the ImportRun's COMPLETED transition -- never on the FAILED-transition helper's path"
  - "resolve.py recomputes trust_tier once after every person_id update and after the outcome branch (paused-with-misses or completed) sets resolve_run.status"
  - "Four DB-gated tests locking the born state, the birth-log row (incl. its oldest-row ordering), the TRUSTED-on-arrival tier, and re-import idempotence"
affects: ["48-06 (publish gate reads a trust_tier every writer now stamps correctly)", "48-09 (recompute-trust --all zero-rows-changed verification depends on all four pipeline writer paths, now fully wired)"]

actuals:
  tokens: 5531
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Offline pipeline commands import api.services.trust.recompute_argument_tier the same way ingest.py already imports api.services.argument_uniqueness -- an established cross-layer pattern, not new architecture"
    - "Birth-state ArgumentStatusLog write placed strictly after the birth Argument's flush succeeds, on the post-flush success path only, so a docket/question conflict rollback can never orphan a status-log row"
    - "recompute_argument_tier called as the LAST write inside each writer's own get_session()/async-with block, never after a session.commit(), so the tier commits atomically with the data that produced it (D-07, 48-RESEARCH.md Pitfall 2)"

key-files:
  created: []
  modified:
    - pipeline/commands/import_convokit.py
    - pipeline/commands/ingest.py
    - pipeline/commands/parse.py
    - pipeline/commands/resolve.py
    - pipeline/tests/test_import_convokit_core.py
    - api/tests/test_admin_dev_routes.py
    - .planning/WINDOWS.md

key-decisions:
  - "Task 1's born-state status kwarg and its Phase 30 comment were already flipped to CANDIDATE by plan 48-04's Rule 3 fix (WINDOWS.md entry 7) -- confirmed already-done, not re-applied, and the ledger entry marked fixed at the end of this plan."
  - "parse.py's recompute call is guarded by `if run.argument_id is not None:` even though the plan's acceptance criteria only requires the literal string to appear twice (import + one call site) -- the guard doesn't change the occurrence count and mirrors the existing `if run.argument_id is not None:` guard already used for the participant-seeding block a few lines above in the same function."
  - "Comments explaining 'no session.commit() is added here' were reworded to 'no explicit commit call is added here' after those comments themselves tripped the acceptance-criteria's own literal grep for the string \"session.commit()\" -- self-inflicted, caught by running the criterion, fixed before commit."

requirements-completed: [TRUST-02, TRUST-03]

coverage:
  - id: D1
    description: "A corpus import creates an Argument at ArgumentStatusEnum.CANDIDATE (the born state) via the explicit kwarg (already correct from 48-04); a PDF ingest creates one via the model default alone, with no explicit status kwarg added."
    requirement: "TRUST-03"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_convokit_core.py::test_corpus_argument_is_born_candidate"
        status: pass
      - kind: other
        ref: "AST check (Task 2 acceptance criteria): every Argument(...) call in pipeline/commands/ingest.py::_run_ingest_inner carries no status= keyword"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every argument gets exactly one ArgumentStatusLog row at creation carrying the born state, and it is the oldest row for that argument when ordered by (created_at, id) -- the same ordering get_argument_detail uses (TRUST-03 ordering edge)."
    requirement: "TRUST-03"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_convokit_core.py::test_corpus_birth_writes_one_candidate_status_log_row"
        status: pass
    human_judgment: false
  - id: D3
    description: "A corpus argument's stored trust_tier reads TRUSTED at import time (not the UNCERTAIN server default) once every constituent resolves; a PDF-ingested argument with zero utterances reads UNCERTAIN, matching the fail-closed default, proving the ingest writer path is wired rather than lucky."
    requirement: "TRUST-02"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_convokit_core.py::test_corpus_argument_tier_is_trusted_on_arrival"
        status: pass
      - kind: other
        ref: "AST check (Task 2 acceptance criteria): recompute_argument_tier appears exactly once in ingest.py's _run_ingest_inner, parse.py, and resolve.py each"
        status: pass
    human_judgment: false
  - id: D4
    description: "Re-running the corpus importer for a conversation that already has an argument creates no second Argument row, no second born-state status-log row, and leaves the stored tier unchanged (TRUST-03 adjacency edge; the idempotent-SKIP early return is preserved)."
    requirement: "TRUST-03"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_convokit_core.py::test_corpus_reimport_adds_no_second_birth_row"
        status: pass
    human_judgment: false
  - id: D5
    description: "The corpus import, PDF ingest, parse, and resolve commands each call recompute_argument_tier inside their own get_session() block, strictly before that block's clean exit -- no session.commit() was introduced anywhere -- so the tier commits atomically with the writes that produced it."
    requirement: "TRUST-02"
    verification:
      - kind: other
        ref: "AST checks (Task 1/2 acceptance criteria): ArgumentStatusLog precedes recompute_argument_tier in _import_conversation's source order; grep -c session.commit() returns 0 for ingest.py/parse.py/resolve.py"
        status: pass
    human_judgment: false
  - id: D6
    description: "Full pipeline and full-repo test suites are green with exactly the one pre-existing known-expected failure (test_admin_detail_contract_does_declare_trust_tier, tracked since 48-03, resolves at 48-07) and zero new/unexpected failures."
    requirement: "TRUST-02"
    verification:
      - kind: other
        ref: "./.venv/bin/python -m pytest -q -> 1 failed (known-expected), 1136 passed, 4 skipped, 5 xfailed"
        status: pass
    human_judgment: false

duration: ~50min
completed: 2026-08-19
status: complete
---

# Phase 48 Plan 05: Pipeline Writer Paths -- Born Candidate, Logged Birth, Tier on Arrival Summary

**Every offline pipeline write path (corpus import, PDF ingest, parse, resolve) now logs an argument's born-`candidate` transition and calls `recompute_argument_tier` inside its own transaction, closing TRUST-03's "born a candidate with its tier set on arrival" criterion for the last unwired writers.**

## Performance

- **Duration:** ~50 min
- **Tasks:** 3/3 complete
- **Files modified:** 7 (4 pipeline commands, 1 pipeline test file, 1 API test file outside declared scope via a documented deviation, 1 ledger file)

## Accomplishments
- `pipeline/commands/import_convokit.py::_import_conversation` writes `ArgumentStatusLog(argument_id=argument.id, status=CANDIDATE)` immediately after the birth `Argument` flush succeeds (post-conflict-rollback-branch only), and calls `recompute_argument_tier(session, argument.id)` as the function's very last statement, after the `AdminJob` pause row -- both inside `run_import_convokit`'s single per-conversation `get_session()` transaction.
- `pipeline/commands/ingest.py::_run_ingest_inner` gains the same `ArgumentStatusLog` birth write and a `recompute_argument_tier` call after the `ImportRun` flush, while its `Argument(...)` construction still carries no explicit `status=` kwarg -- a one-line comment now records that the omission is intentional (relies on the Phase 48 D-01 model default).
- `pipeline/commands/parse.py` recomputes the tier once, on the success path only, right after the `ImportRun`'s `COMPLETED` transition -- never reachable from the separate FAILED-transition helper.
- `pipeline/commands/resolve.py` recomputes the tier once, after every per-label `person_id` update and after the outcome branch (paused-with-misses or completed) has set `resolve_run.status`, using the already-loaded `parse_run.argument_id`.
- Four new DB-gated tests in `pipeline/tests/test_import_convokit_core.py` lock the born state, the single oldest-row birth log, the TRUSTED-on-arrival tier (fully resolved corpus conversation), and re-import idempotence across all three (argument count, log count, tier value).
- `_write_corpus_fixture` in that test file gained an optional `utterances` parameter (default `None` preserves every existing caller's empty-file behavior) so the tier test could supply one real, resolvable turn.
- Full-repo suite: 1136 passed, 4 skipped, 5 xfailed, 1 known-expected failure (`test_admin_detail_contract_does_declare_trust_tier`, resolves at 48-07), 0 unexpected.

## Task Commits

Each task was committed atomically:

1. **Task 1: Corpus import -- born candidate, logged birth, tier on arrival** - `904ff35ce` (feat)
2. **Task 2: PDF path -- ingest birth log, and recompute in parse and resolve** - `3ed8bc22f` (feat)
3. **Task 3: Corpus-import coverage for born state, birth log, tier, and idempotence** - `a45fdef03` (test)

## Files Created/Modified
- `pipeline/commands/import_convokit.py` - `ArgumentStatusLog` birth write + `recompute_argument_tier` call at the end of `_import_conversation` (Task 1)
- `pipeline/commands/ingest.py` - `ArgumentStatusLog` birth write + `recompute_argument_tier` call inside `_run_ingest_inner`, no explicit status kwarg (Task 2)
- `pipeline/commands/parse.py` - `recompute_argument_tier` on the success path after the `COMPLETED` transition (Task 2)
- `pipeline/commands/resolve.py` - `recompute_argument_tier` once after the outcome branch (Task 2)
- `pipeline/tests/test_import_convokit_core.py` - Four new tests + optional `utterances` param on `_write_corpus_fixture` (Task 3)
- `api/tests/test_admin_dev_routes.py` - Corrected a stale zero-row assertion, see Deviations (Task 3 deviation)
- `.planning/WINDOWS.md` - Marked entry 7 (48-04's Rule 3 note about this file's remaining scope) fixed

## Decisions Made
See `key-decisions` in frontmatter for the confirmed-already-done Task 1 kwarg/comment, the `parse.py` argument_id guard, and the self-inflicted grep-collision fix to the explanatory comments.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug in test's assumption] `test_admin_dev_routes.py::test_reset_writes_status_log_rows` asserted zero status-log rows for candidate arguments**
- **Found during:** Task 3's plan-level full-suite verification run (`pytest api/tests pipeline/tests tests -q`).
- **Issue:** This test asserted `ArgumentStatusLog` count `== 0` for two fixture arguments (15169, 22372) described as arguments that "never left the candidate state." That was correct before this plan's Task 1 -- `import_convokit.py` had never written a birth-state log row. Task 1 adds exactly that write (D-03), so those same arguments now correctly carry one row each. This is precisely the consequence 48-CONTEXT.md's D-03 predicted: "every argument now carries a status-log row ... it means the regression test exercises the real path."
- **Fix:** Updated the assertions to expect exactly 1 row (birth only) for the still-candidate arguments and `>= 2` (birth + DRAFT/PUBLISHED) for the arguments that did transition, with a docstring note explaining the D-03 consequence so a future reader isn't confused by the change.
- **Files modified:** `api/tests/test_admin_dev_routes.py` (outside this plan's declared `files_modified`).
- **Verification:** `./.venv/bin/python -m pytest api/tests/test_admin_dev_routes.py -q` -> 9 passed. Full-repo suite re-run afterward confirmed no other regression.
- **Committed in:** `a45fdef03` (Task 3 commit).

---

**Total deviations:** 1 auto-fixed (1 Rule 1 stale-test-assumption fix, in a file outside this plan's declared scope but directly caused by this plan's own Task 1 change).
**Impact on plan:** No architectural change and no scope creep beyond the one-file test fix this plan's own Task 1 necessitated. Grepped for other tests asserting a zero/absent `ArgumentStatusLog` count and found none.

## Issues Encountered

- Two explanatory comments I wrote (in `ingest.py`, `parse.py`, `resolve.py`) contained the literal string `session.commit()` while explaining that no such call was added -- which tripped the plan's own `grep -c "session.commit()" ... returns 0` acceptance criterion. Caught by running the criterion, not by inspection; reworded to "no explicit commit call is added here" with no change in meaning.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All four writer paths in `48-RESEARCH.md`'s "Complete Writer-Path Enumeration" that were this plan's declared scope (rows 1, 2, 3, 5) are now wired: corpus import, PDF ingest, parse, and resolve each recompute `trust_tier` in-transaction with their own writes.
- Plan 48-06 (publish gate) can rely on `arguments.trust_tier` being correctly recomputed by every pipeline writer path, in addition to the `admin_jobs` writers 48-04 already wired.
- Plan 48-09's `recompute-trust --all` zero-rows-changed verification now has all pipeline-side writer paths correctly stamped to be silent against, on top of 48-04's admin-side coverage.
- Per 48-CONTEXT.md's flagged assumption ("`parse.py` and `resolve.py` are wired but not live-verified this phase" -- corpus-first/PDF-deferred scope decision, no PDF fixture in the repo), this plan's `parse.py`/`resolve.py` recompute calls are covered by the existing `pipeline/tests/test_parse.py`/`test_resolve.py` suites not regressing, not by a positive tier assertion against real PDF data. This remains open, tracked at `.planning/notes/2026-08-18-pdf-provenance-live-fixture-verification.md`, to be picked up when the PDF route returns (Phase 50).
- Full suite baseline for subsequent plans: 1136 passed, 4 skipped, 5 xfailed, 1 known-expected failure (`api/tests/test_trust_public_leak_ban.py::test_admin_detail_contract_does_declare_trust_tier`, resolves at 48-07), 0 unexpected.

## Self-Check: PASSED

- FOUND: pipeline/commands/import_convokit.py
- FOUND: pipeline/commands/ingest.py
- FOUND: pipeline/commands/parse.py
- FOUND: pipeline/commands/resolve.py
- FOUND: pipeline/tests/test_import_convokit_core.py
- FOUND: api/tests/test_admin_dev_routes.py
- FOUND commit: 904ff35ce
- FOUND commit: 3ed8bc22f
- FOUND commit: a45fdef03

---
*Phase: 48-trust-lifecycle*
*Completed: 2026-08-19*
