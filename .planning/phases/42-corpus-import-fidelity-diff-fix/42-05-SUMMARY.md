---
phase: 42-corpus-import-fidelity-diff-fix
plan: 05
subsystem: pipeline
tags: [convokit, sqlalchemy, postgres, corpus-import, section-hint, bench-classification]

# Dependency graph
requires:
  - phase: 42-corpus-import-fidelity-diff-fix
    plan: 04
    provides: "Operator D-05/D-06 disposition for all 8 Review Gate items; section_hint derivation (item 1) and bench-tenure warn-only fix (item 2) landed in pipeline/commands/import_convokit.py"
provides:
  - "Proof (not assumption) that every operator-approved real defect from Plan 04 now reads Faithful, or is recorded as an open finding with its observed value, against a freshly re-imported fixture"
  - "Proof that the re-imported fixture's source-turn coverage (479/479), speaker roster, and source-docket set (642) match the raw ConvoKit source exactly"
  - "Proof that Utterance.sequence is stable across a delete-and-reimport cycle (0 differences across all 480 rows)"
  - "Operator confirmation (Task 3, blocking checkpoint) that the fixture's transcript page renders its section-jump anchor as decided"
  - "CORPUS-14 closed"
affects: [43-dev-only-reset-to-fixture]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "When a diff-generator script overwrites its own output document on every run, preserve the pre-fix baseline by generating the post-fix run to a temporary/scratch path first, then hand-merging both into the final committed document (Pre-Fix Baseline section + regenerated post-fix tables + a Post-Fix Verification comparison table) rather than letting the second run silently destroy the first run's evidence."
    - "When capturing before/after evidence files for a WSL/Windows split dev environment, write scratch files to the Windows temp directory (tempfile.gettempdir() under the Windows .venv interpreter) rather than a WSL-only /tmp path — the Windows Python process cannot resolve WSL paths, and vice versa."

key-files:
  created: []
  modified:
    - .planning/CORPUS-FIDELITY-DIFF.md
    - .planning/STATE.md

key-decisions:
  - "The fixture's only real raw side transition after the approved fixes is a single PETITIONER-side turn — no advocate in this conversation's raw advocates dict carries a RESPONDENT side code, and the government's real respondent-side advocate (Thurgood Marshall, then Solicitor General) resolves to BENCH per item 2's operator-approved bench-warn-only disposition (side never reassigned). This is a correct, foreseeable consequence of that disposition on this specific fixture, not a new defect — recorded explicitly in the diff document and confirmed at the Task 3 checkpoint (one 'Petitioner' section-jump link, not three)."
  - "The imported ArgumentParticipant roster (17) is not a strict subset-minus-sentinel of the raw distinct speaker roster (15, after excluding the <INAUDIBLE> unattributed sentinel) — it also includes 2 advocates (Hugh B. Cox, Joseph Auerbach) listed in conversations.json's advocates dict as counsel of record who never personally speak a turn in this transcript. Recorded as correct, unchanged, intentional advocate-resolution-loop behavior, not a defect."
  - "The full pytest -q run's 4 errors in api/tests/test_phase38_people_ui_contract.py are the same pre-existing, unrelated WSL/Windows Node.js path-mangling bug already logged in deferred-items.md by Plans 02 and 04 — confirmed via git status --porcelain showing this plan touched no api/ files. Not fixed here, per the scope-boundary rule and this phase's own established precedent."

requirements-completed: [CORPUS-14]

coverage:
  - id: D1
    description: "The fixture was deleted and re-imported through the fixed importer code path, and the same fidelity comparison was re-run against the fresh rows (not assumed) — every operator-approved real defect (item 1 section_hint, item 2 bench-tenure visibility) now reads Faithful or is recorded as an open finding with its observed value"
    requirement: "CORPUS-14"
    verification:
      - kind: e2e
        ref: "real dev DB: delete_fixture_argument.py --conversation-id 15169 --delete-case --yes -> import-convokit --conversation-id 15169 (1 arguments created, 0 skipped) -> diff_corpus_fixture.py --conversation-id 15169, merged into CORPUS-FIDELITY-DIFF.md's Post-Fix Verification section"
        status: pass
    human_judgment: false
  - id: D2
    description: "Re-imported fixture's source-turn coverage (479/479 raw turns represented), speaker roster, and source-docket set (exactly 642) match the raw ConvoKit source exactly, cross-checked against FIXTURES.md's independently-derived counts with zero divergence"
    requirement: "CORPUS-14"
    verification:
      - kind: e2e
        ref: ".planning/CORPUS-FIDELITY-DIFF.md ## Regression Checks -- Exactness section; FIXTURES.md cross-check table"
        status: pass
    human_judgment: false
  - id: D3
    description: "Utterance.sequence is assigned in streamed transcript order starting at 1 and is stable across the delete-and-reimport cycle"
    requirement: "CORPUS-14"
    verification:
      - kind: e2e
        ref: "pre-delete vs. post-reimport sequence-to-text mapping (480 rows each) compared via PowerShell Compare-Object: 0 differences"
        status: pass
    human_judgment: false
  - id: D4
    description: "No argument other than the fixture was created, modified, or deleted, and no full-corpus or full-term backfill ran"
    requirement: "CORPUS-14"
    verification:
      - kind: e2e
        ref: "arguments total=166, people=343, court_tenures=123, cases term_year=1966=1 all match Plan 01/02 baseline; 163 pre-existing convokit_import pipeline_runs all dated 2026-07-10 (none created during this phase)"
        status: pass
    human_judgment: false
  - id: D5
    description: "The fixture's transcript page renders its section-jump anchor as decided by the operator (bench-warn-only for item 2 means exactly one 'Petitioner' link, not three) and a pre-existing argument's transcript still renders normally"
    requirement: "CORPUS-14"
    verification:
      - kind: manual_procedural
        ref: "Task 3 checkpoint: operator visited http://localhost:5173/admin/pipeline/1231, confirmed one 'Petitioner' section-jump link, Marshall shown as BENCH, replied 'approved'"
        status: pass
    human_judgment: true
    rationale: "Whether the rendered page visually matches the operator's own approved classification choice is a judgment only a human viewing the live page can make -- a database query cannot prove the frontend actually renders the anchors."

duration: 35min (active; Task 3's checkpoint wait time not counted)
completed: 2026-07-30
status: complete
---

# Phase 42 Plan 5: Post-Fix Re-Verification & Operator Transcript-Page Confirmation Summary

**Deleted and re-imported the conversation-15169 fixture through Plan 04's fixed `import_convokit` code path, re-ran the same field-by-field fidelity diff against the fresh rows (not assumed), and got the operator's live-browser confirmation that the transcript page renders exactly the section-jump anchor its approved bench-warn-only disposition implies — closing CORPUS-14.**

## Performance

- **Duration:** ~35 min active work (Task 3's decision-checkpoint wait time is not counted, per this phase's established convention)
- **Started:** 2026-07-30T18:32:31Z (approx, after Plan 04's completion commit)
- **Completed:** 2026-07-30 (Task 3 checkpoint approved)
- **Tasks:** 3 (2 automated + 1 blocking human-verify checkpoint)
- **Files modified:** 2 (`.planning/CORPUS-FIDELITY-DIFF.md`, `.planning/STATE.md`)

## Accomplishments

- **Task 1:** Captured the pre-delete `Utterance.sequence`-to-text mapping (480 rows) to a Windows-temp scratch file, then ran the full cycle: `scripts/delete_fixture_argument.py --conversation-id 15169 --delete-case --yes` (confirmed post-delete count 0) → `python -m pipeline import-convokit --conversation-id 15169` (printed `1 arguments created, 0 arguments skipped`, `0 utterance rows errored`, `5 bench tenure mismatches`) → `scripts/diff_corpus_fixture.py --conversation-id 15169` regenerated to a temp path, then hand-merged into `.planning/CORPUS-FIDELITY-DIFF.md` alongside the preserved Plan 03 Pre-Fix Baseline tables. Added a Post-Fix Verification section comparing all 8 Review Gate items' pre/post verdicts against their recorded dispositions. Proved `Utterance.sequence` ordering stability: 0 differences across all 480 rows, pre-delete vs. post-reimport. Every dev-DB count (arguments=166, people=343, court_tenures=123, cases term_year=1966=1, fixture utterances=480) matched Plan 01/02's recorded baseline exactly.
- **Task 2:** Added a Regression Checks section recording the exactness (ROADMAP success criterion 4) and no-backfill (success criterion 5) claims as observed query results, cross-checked against `.planning/FIXTURES.md`'s independently-derived counts for conversation 15169 (9 advocates, 15 distinct speakers, 8 bench speakers, 479 turns, 2 transcripts) — zero divergence found. Named the imported-roster's two silent-advocate exceptions explicitly (Hugh B. Cox, Joseph Auerbach — listed as counsel of record but never speaking a turn). Confirmed no backfill: 163 pre-existing `convokit_import` pipeline_runs all dated 2026-07-10, none created during this phase. Full suite (`pytest -q`): 823 passed, 5 xfailed, 4 errors (the same pre-existing, unrelated WSL/Windows Node.js path bug already logged by Plans 02 and 04). No code was touched by this task.
- **Task 3 (checkpoint:human-verify, gate=blocking):** The operator visited the correct admin page (`http://localhost:5173/admin/pipeline/1231`, the fixture's `admin_jobs.id`) and confirmed the transcript page shows exactly one "Petitioner" section-jump link (not three — because Marshall, the fixture's only real respondent-side advocate, still resolves to BENCH under the operator's own approved bench-warn-only disposition), that the link jumps correctly, that Marshall is still shown as a member of the Court, and that a pre-existing argument's transcript still renders normally. Replied "approved."

## Task Commits

Each task was committed atomically:

1. **Task 1: Post-fix delete, re-import, and re-run of the same comparison** - `97f67cf5` (feat)
2. **Task 2: Exactness and no-backfill regression checks** - `3ae341fe` (test)
3. **Task 3: Confirm the fixture's transcript page renders as decided** - no commit (checkpoint-only; operator confirmation via live browser session produced no code/doc change)

Interim STATE.md decision/session recording (between Task 2 and Task 3's confirmation): `e713bb99` (docs)

_No `docs: complete plan` metadata commit exists yet — that follows this SUMMARY._

## Files Created/Modified

- `.planning/CORPUS-FIDELITY-DIFF.md` — Restructured into a Pre-Fix Baseline section (Plan 03's original tables, preserved verbatim) plus regenerated post-fix tables (cases, arguments, utterances, people, argument_participants, court_tenures, Volume and Roster Exactness), a new Post-Fix Verification section (per-item pre/post verdict comparison tied to the operator's recorded disposition, plus the section_hint single-link finding and the ordering-stability record), and a new Regression Checks section (exactness cross-check against FIXTURES.md, no-backfill query results, suite health). Disposition, Fixes Applied, Out of Scope, and Consumers sections carried forward with light updates.
- `.planning/STATE.md` — Recorded two decisions (Task 1's ordering/section-hint finding, Task 2's exactness cross-check and roster-exception finding) and updated Session Continuity to reflect the checkpoint-pending, then checkpoint-approved, position.

## Decisions Made

- The fixture's transcript page legitimately shows only one section-jump link ("Petitioner"), not the three (Petitioner/Respondent/Rebuttal) a naive reading of Task 3's prose might suggest — because no advocate in this conversation's raw `advocates` dict carries a RESPONDENT side code, and the one person who actually argued for the respondent (Thurgood Marshall, then Solicitor General) resolves to BENCH under the operator's own item-2 `bench-warn-only` choice. This was flagged explicitly in the diff document *before* the checkpoint was presented, so the operator's "approved" response is an informed confirmation, not a surprised one.
- The imported `ArgumentParticipant` roster (17) legitimately exceeds the raw distinct speaker roster minus the unattributed sentinel (15) by exactly 2 — Hugh B. Cox and Joseph Auerbach, both listed as counsel of record in `conversations.json`'s `advocates` dict but who never personally speak a turn in this transcript. This is intentional advocate-resolution-loop behavior (every listed advocate gets a participant row regardless of whether they spoke), not a defect, and was documented as such rather than silently treated as a discrepancy.
- The full-suite `pytest -q`'s 4 pre-existing, unrelated `api/tests/test_phase38_people_ui_contract.py` errors were recorded as observed (not hidden) and left unfixed, consistent with the identical decision already made twice in this same phase (Plans 02 and 04) — confirmed via `git status --porcelain pipeline api app scripts` that this task touched none of those directories.

## Deviations from Plan

**1. [Scope-boundary observation, not a fix] `scripts/diff_corpus_fixture.py --out` cannot write to a WSL-style path from the Windows `.venv` interpreter.**
- **Found during:** Task 1, attempting to regenerate the diff to a temporary scratch path outside the repo.
- **Issue:** `Path(args.out).write_text(...)` raised `FileNotFoundError` when `--out` was given a `/tmp/...` path, because the script runs under the Windows `.venv/Scripts/python.exe` (via WSL interop) and cannot resolve a WSL-only path.
- **Fix:** Regenerated to a Windows temp path (`C:\Users\jason\AppData\Local\Temp\CORPUS-FIDELITY-DIFF.post-fix.md`) instead, then copied the result into the WSL-side scratchpad via the WSL-visible `/mnt/c/...` mount for merging. No code change — this is an environment-usage adjustment, not an importer or script defect (the WSL/Windows split dev-env memory note already documents this pattern).
- **Files modified:** None (workflow-only; the final merged document was written directly to `.planning/CORPUS-FIDELITY-DIFF.md` via the `Write` tool, not via the script's own `--out`).
- **Verification:** The merged document's automated verify commands (both Task 1's and Task 2's) passed.

**2. [Rule 1-adjacent honest recording, not a fix] The full `pytest -q` run's 4 pre-existing errors technically fail Task 2's literal "exits 0 with zero failures and zero errors" acceptance wording.**
- **Found during:** Task 2's required verify command.
- **Issue:** `pytest -q` (whole suite) returned non-zero (4 errors) due to the same pre-existing WSL/Windows Node.js path bug in `api/tests/test_phase38_people_ui_contract.py` first logged by Plan 02 and observed again by Plan 04.
- **Why not fixed:** Confirmed via `git status --porcelain pipeline api app scripts` that this task modified none of those directories; the failure reproduces identically outside this plan's scope and predates this session. Per the scope-boundary rule and this phase's own established precedent (Plans 02 and 04 both hit and logged the identical failure without treating it as blocking), this was recorded honestly in the Regression Checks section rather than silently declared "green."
- **Action taken:** Documented in `.planning/CORPUS-FIDELITY-DIFF.md`'s Regression Checks → Suite health subsection with exact counts (823 passed, 5 xfailed, 4 errors) and a cross-reference to `deferred-items.md`. `pipeline/tests/ -q` alone (the actual code this plan's own dispositions touch) is fully green: 226 passed, 5 xfailed.
- **Files modified:** `.planning/CORPUS-FIDELITY-DIFF.md` only.

---

**Total deviations:** 2 (1 environment-usage workaround, 1 honest-recording-not-fix of an already-established pre-existing issue). **Impact on plan:** None on scope or correctness — no importer or script code was changed by either deviation, and both are fully documented.

## Issues Encountered

None beyond the deviations above.

## User Setup Required

None — no external service configuration required. The operator's Task 3 verification used the already-running dev servers.

## Next Phase Readiness

- **CORPUS-14 is closed.** The fixture was re-imported cleanly through the fixed code path, the same comparison was re-run (not assumed), every operator-approved real defect either reads Faithful or is recorded as an open finding with its observed value, all 479 raw source turns are represented with zero errored rows, the roster and source-docket set match the raw source exactly (cross-checked against FIXTURES.md with zero divergence), no other argument was touched, no backfill ran, and the operator confirmed the transcript page renders as their own disposition implies.
- **Phase 43 (Dev-Only Reset to Fixture) can proceed directly on the tooling this phase built.** `scripts/delete_fixture_argument.py` (Plan 02) and the `--conversation-id` scoped import path (Plan 01) are both directly reusable by Phase 43's reset tool, which needs to land four conversations across four different terms (the full `.planning/FIXTURES.md` fixture set) without pulling in each term's other conversations — exactly the isolation both scripts were purpose-built to provide. This delete-then-reimport round trip, now proven twice in this phase (once with no importer changes in Plan 02, once with two real importer fixes in this plan), is the reference pattern Phase 43 should follow for each of its four fixtures.
- **Deferred, not blocking:** the pre-existing WSL/Windows Node.js path bug (`api/tests/test_phase38_people_ui_contract.py`, logged by Plan 02) and the order-dependent `roles.name` UniqueViolation (`api/tests/test_speakers_service.py`, logged by Plan 04) both remain in `.planning/phases/42-corpus-import-fidelity-diff-fix/deferred-items.md` for a future session that owns either the WSL/Windows dev split or `api/tests/conftest.py`'s transaction-rollback ordering.
- **Item 8 (Person-dedup mismatch: White/Black/Clark/Douglas duplicate Person rows) remains deliberately deferred**, per the operator's explicit scope decision recorded in Plan 04's Disposition section — confirmed unchanged by this plan's re-verification (same 4 Mis-mapped `court_tenures` rows, same duplicate Person ids). A future phase should scope a proper name-normalization/fuzzy-match fix across the whole corpus, not an improvised per-fixture patch.
- No blockers for Phase 43. `pipeline/tests/` fully green (226 passed, 5 pre-existing xfailed). The fixture remains present in `scotus` at the end of this plan (Argument id 1864, Case id from the fresh re-import), as required for Phase 43 and Phase 45's dependent work.

---
*Phase: 42-corpus-import-fidelity-diff-fix*
*Completed: 2026-07-30*

## Self-Check: PASSED

- FOUND: .planning/phases/42-corpus-import-fidelity-diff-fix/42-05-SUMMARY.md
- FOUND commit: 97f67cf5 (Task 1)
- FOUND commit: 3ae341fe (Task 2)
- FOUND commit: e713bb99 (interim STATE.md decision/session recording)
