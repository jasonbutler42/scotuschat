---
phase: 42-corpus-import-fidelity-diff-fix
plan: 04
subsystem: pipeline
tags: [convokit, sqlalchemy, corpus-import, section-hint, bench-classification, apolitical]

# Dependency graph
requires:
  - phase: 42-corpus-import-fidelity-diff-fix
    plan: 03
    provides: "scripts/diff_corpus_fixture.py; .planning/CORPUS-FIDELITY-DIFF.md with an 8-item numbered Review Gate agenda"
provides:
  - "The operator's D-05/D-06 batch disposition for all 8 Review Gate items, recorded verbatim in .planning/CORPUS-FIDELITY-DIFF.md's Disposition section"
  - "section_hint derivation in _import_utterances (item 1) -- non-cascading petitioner/respondent/rebuttal/amicus semantics matching parse.py's precedent, restoring the transcript page's section-jump anchors for corpus-imported arguments"
  - "A bench_tenure_mismatch counter + warning in _resolve_and_link_participant (item 2, option bench-warn-only) -- visibility only, ArgumentParticipant.side is never reassigned"
  - "A documentation-completeness note on apolitical.py's module docstring (item 6) -- FORBIDDEN_FIELDS unchanged"
  - "A Fixes Applied section in .planning/CORPUS-FIDELITY-DIFF.md tying every change (or explicit no-change) to its Review Gate item number"
affects: [42-05-corpus-import-fidelity-diff-fix]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "section_hint derivation tracks two locals across a conversation's WHOLE turn loop (current_section_side, respondent_section_started) rather than a per-turn state machine, since the corpus importer has no page-by-page TOC markers to key off of the way parse.py does -- a side change relative to current_section_side is what opens a new section, not a marker string"
    - "A bench-classification tenure cross-check is threaded through as an optional keyword parameter (argued_date=None) rather than a required one, so every pre-existing caller/test Namespace continues to work unchanged and the check is a no-op whenever no parseable transcript date exists"
    - "Warn-only visibility (counter + print) is implemented as the exact same tenure-coverage query bench-general would use, with only the branch that would reassign `side` omitted -- keeping the two options a single code path apart if a later phase upgrades from warn-only to general"

key-files:
  created:
    - pipeline/tests/test_import_convokit_bench_tenure.py
  modified:
    - pipeline/commands/import_convokit.py
    - pipeline/corpus/apolitical.py
    - pipeline/tests/test_import_convokit_utterances.py
    - .planning/CORPUS-FIDELITY-DIFF.md
    - .planning/phases/42-corpus-import-fidelity-diff-fix/deferred-items.md

key-decisions:
  - "Operator disposition (2026-07-30, D-05/D-06 batch review): item 1 approved as real defect, option section-hint-derive. Item 2 approved as real defect, option bench-warn-only (NOT bench-general) -- side is never reassigned for Marshall's fixture row; the operator explicitly wants any person-identity/classification-merging work deferred to a later phase. Items 3-7 approved as proposed, no code change. Item 8 (the new Person-dedup finding) approved as a real-defect candidate but flagged only -- a proper fix touches every justice in the corpus and deserves its own research/plan cycle, not an improvised mid-checkpoint fix."
  - "bench_tenure_mismatch counter and warning use the identical read-only CourtTenure query bench-general would use; only the side-reassignment branch was omitted for bench-warn-only, so upgrading to bench-general later is a small, isolated diff."
  - "Logged a pre-existing, unrelated api/tests failure (roles.name UniqueViolation on 'Associate Justice' in test_speakers_service.py) to deferred-items.md rather than fixing it -- confirmed via git diff that no file this plan touched is involved, and it reproduces on a fresh api/tests run with no prior test executed. Root cause hypothesis: api/tests/conftest.py::db_session's explicit rollback() runs inside session.begin()'s own context block, so that block's own commit-on-clean-exit may run after the manual rollback, allowing a test-created row to leak permanently into whichever DB DATABASE_URL points to."

requirements-completed: [CORPUS-14]

coverage:
  - id: D1
    description: "All 8 numbered Review Gate items in .planning/CORPUS-FIDELITY-DIFF.md carry the operator's recorded disposition (approve/adjust/decline plus chosen option id), written before any importer code changed"
    requirement: "CORPUS-14"
    verification:
      - kind: manual_procedural
        ref: ".planning/CORPUS-FIDELITY-DIFF.md ## Disposition section, all 8 items present with option ids and review date 2026-07-30"
        status: pass
    human_judgment: false
  - id: D2
    description: "section_hint is derived non-cascadingly (petitioner/respondent/rebuttal/amicus) in _import_utterances, matching parse.py's semantics; BENCH/UNKNOWN/no-speaker rows never carry or change it"
    requirement: "CORPUS-14"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_utterances.py (6 new tests: petitioner-only single-hint, respondent-after-petitioner, rebuttal-not-second-petitioner, bench-never-changes-section, full-sequence exact-count, zero-turns-no-crash)"
        status: pass
      - kind: unit
        ref: "pipeline/tests/test_parse.py::test_section_hint_not_cascade (PDF-pipeline precedent, unmodified)"
        status: pass
    human_judgment: false
  - id: D3
    description: "A speaker typed a Justice with no CourtTenure row covering argued_date is flagged (bench_tenure_mismatch counter + warning naming speaker id/argued_date/earliest tenure start) but ArgumentParticipant.side is never reassigned (bench-warn-only); inclusive start boundary; null-argued_date fallback preserves today's behavior; no Person.is_justice or CourtTenure write"
    requirement: "CORPUS-14"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_bench_tenure.py (4 tests: equal-start-date-covers, one-day-later-mismatch-side-unchanged, no-write-to-CourtTenure-or-is_justice, null-argued_date-fallback)"
        status: pass
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_core.py::test_justice_type_speaker_resolves_to_bench_side (pre-existing test, unmodified, still passing)"
        status: pass
      - kind: other
        ref: "grep -vE '^\\s*#' pipeline/commands/import_convokit.py | grep -cE 'delete\\(CourtTenure|update\\(CourtTenure|CourtTenure\\(' -- returns 0"
        status: pass
    human_judgment: false
  - id: D4
    description: "is_eq_divided documentation-completeness note added to apolitical.py's docstring without adding is_eq_divided to FORBIDDEN_FIELDS or changing either extractor's returned keys"
    requirement: "CORPUS-14"
    verification:
      - kind: manual_procedural
        ref: "pipeline/corpus/apolitical.py module docstring; FORBIDDEN_FIELDS frozenset and both extractors' return dicts diffed unchanged"
        status: pass
    human_judgment: false
  - id: D5
    description: "No conversation other than 15169 was imported during this plan; the fixture's row counts are unchanged"
    requirement: "CORPUS-14"
    verification:
      - kind: other
        ref: "select count(*) from cases where term_year = 1966 -> 1; select count(*) from arguments where oyez_transcript_id = '15169' -> 1 (queried directly against DATABASE_URL after both task commits)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Full pipeline test suite green after both tasks"
    requirement: "CORPUS-14"
    verification:
      - kind: unit
        ref: "./.venv/Scripts/python.exe -m pytest pipeline/tests/ -q"
        status: pass
    human_judgment: false

duration: 38min
completed: 2026-07-30
status: complete
---

# Phase 42 Plan 4: Operator Review Gate, section_hint Derivation & Bench-Tenure Warn-Only Fix Summary

**Recorded the operator's D-05/D-06 batch disposition for all 8 Review Gate items, implemented non-cascading `section_hint` derivation (item 1) restoring the transcript page's section-jump anchors, and added a bench-tenure mismatch warning/counter (item 2, `bench-warn-only`) that flags Thurgood Marshall's pre-tenure BENCH classification without reassigning his fixture row's side.**

## Performance

- **Duration:** 38 min (active coding/testing after the operator's checkpoint disposition was received; Task 1's own decision-checkpoint wait time is not counted)
- **Started:** 2026-07-30T18:00:00Z (approx, after operator disposition received)
- **Completed:** 2026-07-30T18:29:24Z (per final task commit)
- **Tasks:** 3 (Task 1 checkpoint + Task 2 + Task 3)
- **Files modified:** 6 (1 created, 5 modified)

## Accomplishments

- **Task 1 (checkpoint:decision, gate=blocking):** Presented the full `.planning/CORPUS-FIDELITY-DIFF.md` Review Gate section (all 8 numbered items, including item 8's new Person-dedup finding not anticipated by the plan's own `<options>` block) to the operator. No code was touched before the disposition was recorded. The operator's clarifying round distinguished item 2 (Marshall's single-Person timing anomaly) from item 8 (White/Black/Clark/Douglas's duplicate-Person mechanism) before confirming `bench-warn-only` for item 2 specifically.
- **Task 2:** Recorded all 8 dispositions verbatim in a new Disposition section of `.planning/CORPUS-FIDELITY-DIFF.md` (review date 2026-07-30), then implemented `section_hint` derivation in `_import_utterances` for the approved `section-hint-derive` option: a `PETITIONER`/`RESPONDENT`/`AMICUS`-side row whose resolved side differs from the side that opened the current section starts a new one; a petitioner side returning after a respondent section already opened is labeled `rebuttal`, not a second `petitioner`. Six new tests cover petitioner-only, respondent-after-petitioner, rebuttal, bench-never-changes-section, a full multi-section sequence with an exact-count assertion, and a zero-turns no-crash case.
- **Task 3:** Implemented the approved `bench-warn-only` option for item 2: threaded `argued_date` into `_resolve_and_link_participant` and `_import_utterances`, added a read-only `_check_bench_tenure_mismatch` helper (inclusive tenure start boundary, open-ended `end_date` treated as active), a new `bench_tenure_mismatch` summary counter, and a warning naming the speaker id/argued_date/earliest tenure start on record. `side` is never reassigned — per the operator's explicit choice, Marshall's fixture participant row stays BENCH. Added the `is_eq_divided` documentation-completeness note to `apolitical.py` (item 6) without touching `FORBIDDEN_FIELDS`. Appended a Fixes Applied section to the diff document tying every change to its Review Gate item number. Four new tests cover the exact boundary pair (equal-start-date covers; one-day-later mismatches) plus a no-write assertion and a null-`argued_date` fallback.
- Verified directly against the real dev DB (via `DATABASE_URL`, not the test DB) that `cases where term_year = 1966` and `arguments where oyez_transcript_id = '15169'` are both still exactly 1 — no full-corpus or full-term import ran during this plan.

## Task Commits

Each task was committed atomically:

1. **Task 1: Operator batch review checkpoint** — no commit (decision-only; the checkpoint itself produced no code change)
2. **Task 2: Record dispositions, apply section_hint fix** — `daca8bc0` (test)
3. **Task 3: Apply bench-tenure warn-only fix** — `421856c2` (feat)

_No `docs: complete plan` metadata commit exists yet — that follows this SUMMARY._

## Files Created/Modified

- `pipeline/commands/import_convokit.py` — `_import_utterances` derives `section_hint`; `_resolve_and_link_participant` gained `argued_date` and the bench-tenure mismatch check; `_SUMMARY_COUNTER_KEYS`/`_print_summary` gained `bench_tenure_mismatch`; new `_check_bench_tenure_mismatch` helper; `CourtTenure` and `or_` newly imported.
- `pipeline/corpus/apolitical.py` — module docstring gained the `is_eq_divided` documentation-completeness paragraph; no change to `FORBIDDEN_FIELDS` or either extractor's returned keys.
- `pipeline/tests/test_import_convokit_utterances.py` — 6 new `section_hint` tests plus a zero-turns test.
- `pipeline/tests/test_import_convokit_bench_tenure.py` — new file, 4 tests for the bench-tenure boundary pair, no-write assertion, and null-`argued_date` fallback.
- `.planning/CORPUS-FIDELITY-DIFF.md` — new Disposition section (all 8 items) and new Fixes Applied section (per-item change/no-change record).
- `.planning/phases/42-corpus-import-fidelity-diff-fix/deferred-items.md` — logged the pre-existing, unrelated `api/tests` `roles.name` UniqueViolation.

## Decisions Made

- The operator's own words, quoted verbatim in the diff document's Disposition section: "This won't be common but this is a perfect situation to address. Ideally, someone who has been on both sides of the bench should resolve to the same person but for now, I'm okay with them being two separate entries. Defer resolving them into the same person until a later phase." This governed both the `bench-warn-only` choice for item 2 (no `side` reassignment — that felt adjacent to person-identity-merging work) and the flag-only disposition for item 8 (the duplicate-Person finding).
- `bench_tenure_mismatch`'s tenure-coverage query is written identically to what `bench-general` would use, with only the side-reassignment branch omitted — so a later phase choosing to upgrade from warn-only to general is a small, isolated diff rather than a rewrite.
- Logged (did not fix) a pre-existing `api/tests` failure unrelated to any file this plan touches (see Deviations below) — consistent with how 42-02's SUMMARY handled an analogous pre-existing WSL/Windows path bug in the same test run.

## Deviations from Plan

**1. [Scope-boundary deferral, not a fix] Pre-existing `roles.name` UniqueViolation in `api/tests/test_speakers_service.py`**
- **Found during:** Task 3's required `./.venv/Scripts/python.exe -m pytest api/tests -q` verify command.
- **Issue:** 5 failures + the 4 already-documented (42-02) WSL/Windows Node.js path-mangling errors in `test_phase38_people_ui_contract.py`. The 5 new failures are `IntegrityError: duplicate key value violates unique constraint "roles_name_key" DETAIL: Key (name)=(Associate Justice) already exists`, raised by `test_speakers_service.py` tests that unconditionally `Role(name="Associate Justice"); db_session.add(role)`, assuming per-test rollback isolates it.
- **Why not fixed:** None of this plan's two tasks touch `api/tests/conftest.py`, `api/core/database.py`, `Role`, or `test_speakers_service.py` — confirmed via `git diff --stat HEAD~1 HEAD -- api/` returning empty for both task commits. The failure reproduces identically on a fresh `api/tests` run with nothing else run first, meaning the offending `roles` row's persistence predates this session. Root-cause hypothesis (documented, not fixed): `db_session`'s explicit `rollback()` call runs inside `session.begin()`'s own context block, so that block's commit-on-clean-exit may still run afterward, letting a test-created row leak permanently into whichever database `DATABASE_URL` points to.
- **Action taken:** Logged to `.planning/phases/42-corpus-import-fidelity-diff-fix/deferred-items.md` with full reproduction details, per the scope-boundary rule (pre-existing, unrelated-file failures are out of scope for auto-fix).
- **Files modified:** `.planning/phases/42-corpus-import-fidelity-diff-fix/deferred-items.md` only.
- **Verification:** `pipeline/tests/ -q` — this plan's actual required gate for both Task 2 and Task 3 — is fully green (226 passed, 5 pre-existing xfailed, both times).

---

**Total deviations:** 1 (scope-boundary deferral, logged not fixed).
**Impact on plan:** None — this plan's own required verification gate (`pipeline/tests/`) is fully green; the `api/tests` failure is pre-existing DB-pollution/fixture-ordering environmental noise unrelated to any file this plan touched.

## Issues Encountered

None beyond the deviation above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 05 re-runs `scripts/diff_corpus_fixture.py` against the fixture and should now show, relative to the pre-fix document:
  - **`Utterance.section_hint`** — no longer null on 480/480 rows; exactly one non-null hint per petitioner/respondent/rebuttal/amicus section for conversation 15169. The transcript page's section-jump anchors should now render.
  - **Bench classification (item 2, Marshall)** — **UNCHANGED by design.** Plan 05 should confirm Marshall's `ArgumentParticipant.side` is STILL `BENCH` (the operator chose warn-only, not a reassignment) and should instead look for the new `bench_tenure_mismatch` counter and warning appearing in the batch summary/logs when the fixture is re-imported.
  - **Items 3-7** — no diff-document change expected beyond the recorded disposition (no code path was touched).
  - **Item 8 (Person-dedup: White/Black/Clark/Douglas)** — **UNCHANGED by design**, flagged only; still expect 4 duplicate-Person rows with zero `CourtTenure` coverage. This is deliberately deferred to a future phase per the operator's explicit decision.
- The pre-existing, unrelated `api/tests` `roles.name` UniqueViolation (this plan) and the WSL/Windows Node.js path bug (42-02) both remain logged in `.planning/phases/42-corpus-import-fidelity-diff-fix/deferred-items.md` for a future session that owns either `api/tests/conftest.py` or the WSL/Windows dev-split.
- No blockers for Plan 05. `pipeline/tests/` fully green (226 passed, 5 pre-existing xfailed). The fixture's row counts are unchanged (`cases` term_year=1966 count 1; `arguments` oyez_transcript_id=15169 count 1), confirmed directly against the real dev DB.

---
*Phase: 42-corpus-import-fidelity-diff-fix*
*Completed: 2026-07-30*

## Self-Check: PASSED

- FOUND: pipeline/tests/test_import_convokit_bench_tenure.py
- FOUND: pipeline/commands/import_convokit.py
- FOUND: pipeline/corpus/apolitical.py
- FOUND: pipeline/tests/test_import_convokit_utterances.py
- FOUND: .planning/CORPUS-FIDELITY-DIFF.md
- FOUND: .planning/phases/42-corpus-import-fidelity-diff-fix/deferred-items.md
- FOUND: .planning/phases/42-corpus-import-fidelity-diff-fix/42-04-SUMMARY.md
- FOUND commit: daca8bc0 (Task 2)
- FOUND commit: 421856c2 (Task 3)
