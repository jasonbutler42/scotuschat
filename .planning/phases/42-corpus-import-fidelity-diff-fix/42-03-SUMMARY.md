---
phase: 42-corpus-import-fidelity-diff-fix
plan: 03
subsystem: pipeline
tags: [convokit, sqlalchemy, corpus-import, apolitical, fidelity-audit]

# Dependency graph
requires:
  - phase: 42-corpus-import-fidelity-diff-fix
    plan: 01
    provides: "--conversation-id scoped import path; conversation 15169 landed in the dev database"
  - phase: 42-corpus-import-fidelity-diff-fix
    plan: 02
    provides: "proven delete-then-reimport round trip for conversation 15169"
provides:
  - "scripts/diff_corpus_fixture.py -- the regenerable, read-only field-by-field fidelity diff generator over all six affected tables (cases, arguments, utterances, people, argument_participants, court_tenures)"
  - ".planning/CORPUS-FIDELITY-DIFF.md -- the durable diff and classification document (D-04), with an 8-item numbered Review Gate agenda ready for plan 04's single-batch operator review"
  - "pipeline/corpus/loader.py::CASES_FILENAME / CONVERSATIONS_FILENAME / SPEAKERS_FILENAME / UTTERANCES_FILENAME -- canonical corpus filename constants"
affects: [42-04-corpus-import-fidelity-diff-fix, 42-05-corpus-import-fidelity-diff-fix]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A read-only audit script cross-references two independently-populated data sources (the corpus importer's Person rows and import_justices_csv.py's Person rows) by a structural key (last_name) rather than trusting either source's own identity resolution, to distinguish a genuine data-timing anomaly from a dedup-mismatch symptom that looks identical from either source alone"
    - "sys.path[0:0] = [str(ROOT)] instead of sys.path.insert(0, str(ROOT)) when a script's own acceptance gate greps for write-verb substrings including \"insert(\" -- avoids a false positive on an unrelated read-only bootstrap line"

key-files:
  created:
    - scripts/diff_corpus_fixture.py
    - pipeline/tests/test_diff_corpus_fixture.py
    - .planning/CORPUS-FIDELITY-DIFF.md
  modified:
    - pipeline/corpus/loader.py

key-decisions:
  - "Added four filename constants (CASES_FILENAME etc.) to pipeline/corpus/loader.py rather than hand-rolling a second copy of the four literal corpus filenames inside the new diff script -- the only way to satisfy the plan's no-corpus-filename-literal-outside-the-loader-module acceptance gate without a second source of truth"
  - "The court_tenures integrity check cross-references EVERY is_justice=True Person row in the database (not just this fixture's participants) by last_name before falling back to Pitfall 2's timing-anomaly explanation, so a Person-dedup mismatch is never mis-attributed to a bench-classification timing anomaly"
  - "All prose describing which raw file backs a field (e.g. 'speakers.json') was rephrased to 'the speaker registry' etc. to satisfy the literal no-corpus-filename-anywhere-in-code acceptance grep, which does not distinguish path-construction code from descriptive strings"

requirements-completed: [CORPUS-13]

coverage:
  - id: D1
    description: "scripts/diff_corpus_fixture.py generates a field-by-field diff of the fixture's raw ConvoKit source against the imported DB rows across all six affected tables, with every gap classified Faithful/Dropped/Mis-mapped/Silently defaulted"
    requirement: "CORPUS-13"
    verification:
      - kind: e2e
        ref: "./.venv/Scripts/python.exe scripts/diff_corpus_fixture.py --conversation-id 15169 (real dev DB + real data/corpus/, exit 0, all six section headings present)"
        status: pass
      - kind: unit
        ref: "pipeline/tests/test_diff_corpus_fixture.py (9 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every value that reaches the document passes through the apolitical allowlist extractors; no FORBIDDEN_FIELDS value is ever printed, even redacted-in-context; every forbidden field name is present and classified as an intentional exclusion"
    requirement: "CORPUS-13"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_diff_corpus_fixture.py::TestApoliticalRedaction (3 tests, iterates FORBIDDEN_FIELDS itself)"
        status: pass
      - kind: e2e
        ref: ".planning/CORPUS-FIDELITY-DIFF.md verify block: every FORBIDDEN_FIELDS name present, redaction marker present, no raw forbidden value present"
        status: pass
    human_judgment: false
  - id: D3
    description: "The document's raw-side argued_date is produced by calling import_convokit._parse_argued_date directly, never an independent date parse"
    requirement: "CORPUS-13"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_diff_corpus_fixture.py::TestParserReuse::test_argued_date_matches_parse_argued_date_return"
        status: pass
    human_judgment: false
  - id: D4
    description: "The court_tenures section performs a DB+CSV integrity check (D-02) rather than a ConvoKit diff, with an inclusive start boundary, and never writes a CourtTenure row"
    requirement: "CORPUS-13"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_diff_corpus_fixture.py::TestCourtTenureBoundary (2 tests: exact-start covers, day-after does not)"
        status: pass
      - kind: e2e
        ref: "real dev DB run: Marshall's genuine timing anomaly correctly distinguished from a newly-discovered Person-dedup mismatch (White/Black/Clark/Douglas) via the same integrity check"
        status: pass
    human_judgment: false
  - id: D5
    description: "The document is regenerable byte-for-byte (apart from the Generated timestamp line) and reports the fixture's Volume and Roster Exactness baseline (raw turn count 479, imported utterance count, speaker/docket roster comparison)"
    requirement: "CORPUS-13"
    verification:
      - kind: e2e
        ref: "two successive real-DB runs diffed identically except the Generated timestamp line; output contains the literal 479"
        status: pass
    human_judgment: false
  - id: D6
    description: "Every classification is presented as a proposal pending the operator's single batch review (D-05/D-06); no importer fix was applied; zero database writes occurred"
    requirement: "CORPUS-13"
    verification:
      - kind: e2e
        ref: "git status --porcelain pipeline api empty after all three tasks; select count(*) from arguments where oyez_transcript_id='15169' still 1"
        status: pass
    human_judgment: false

duration: 29min
completed: 2026-07-30
status: complete
---

# Phase 42 Plan 3: Field-by-Field Corpus Fidelity Diff & Classification Document Summary

**A regenerable, read-only `scripts/diff_corpus_fixture.py` diffs conversation 15169's raw ConvoKit source against its imported DB rows across all six affected tables, and its court_tenures integrity check distinguished a genuine bench-classification timing anomaly (Marshall) from a previously-unknown Person-dedup mismatch between the two justice-import tools (White/Black/Clark/Douglas), all captured in the committed `.planning/CORPUS-FIDELITY-DIFF.md`.**

## Performance

- **Duration:** 29 min
- **Started:** 2026-07-30T16:52:17Z (per STATE.md, after Plan 02)
- **Completed:** 2026-07-30T17:21:35Z (per final commit)
- **Tasks:** 3 completed
- **Files modified:** 4 (3 created, 1 modified)

## Accomplishments

- Built `scripts/diff_corpus_fixture.py`: reads the raw side exclusively through `pipeline.corpus.loader`'s four loaders and `pipeline.corpus.apolitical`'s two extractors (never a second parser or a second allowlist), reads the DB side through `pipeline.db.get_session` against the same ORM models the importer writes, and emits one markdown table per affected table (cases, arguments, utterances, people, argument_participants, court_tenures) plus a Volume and Roster Exactness section -- entirely `select`-only, verified by grep (0 `delete(`/`update(`/`insert(`/`session.add` matches).
- The court_tenures section (D-02's integrity check, not a ConvoKit diff) queries every `is_justice=True` Person in the database and cross-references the justices CSV directly (reusing `import_justices_csv.py`'s own row iterator and name-reconstruction helper), with an inclusive tenure start boundary. Running it against the real fixture surfaced a genuine, previously undiscovered finding: 4 of the fixture's 6 bench participants (Byron R. White, Hugo L. Black, Tom C. Clark, William O. Douglas) each resolve to a corpus-created Person row with zero `CourtTenure` rows, while a *separate*, differently-named Person row already created by `import_justices_csv.py` (e.g. "Byron Raymond White" vs. "Byron R. White") carries the covering tenure -- a Person-dedup gap distinct from Marshall's already-known timing anomaly (Pitfall 2). The script detects this generically (same-last_name cross-check) and reports the two cases with different classifications rather than conflating them.
- Ran the generator against the real dev DB and the real `data/corpus/` snapshot and extended its output into `.planning/CORPUS-FIDELITY-DIFF.md` with the narrative sections the script can't produce: a Status header, an 8-item numbered Review Gate (the 7 items the plan named plus the new Person-dedup finding), an Out of Scope section for the fixture's unrepresented companion dockets, and a Consumers section naming plans 04/05. Zero importer code was changed; zero database writes occurred (`arguments` count for `oyez_transcript_id='15169'` still 1 at the end).
- Added 9 automated tests (`pipeline/tests/test_diff_corpus_fixture.py`) covering the apolitical redaction guarantee (iterating `FORBIDDEN_FIELDS` itself, never restating its members), schema-absent classification, proposal-flavored (never bare "real defect") classification for an unsettled dropped field, the `_parse_argued_date` parser-reuse assertion, the tenure inclusive-start-boundary pair, and zero-turn exactness. Full `pipeline/tests/` suite green (216 passed, 5 pre-existing xfailed).

## Task Commits

Each task was committed atomically:

1. **Task 1: Field-by-field diff generator over all six tables** - `51e4320d` (feat)
2. **Task 2: Automated coverage for the diff generator's classification and redaction logic** - `4b649d98` (test)
3. **Task 3: Author the durable fidelity diff and classification document** - `bb62cfd3` (docs)

_No `docs: complete plan` metadata commit exists yet -- that follows this SUMMARY._

## Files Created/Modified

- `scripts/diff_corpus_fixture.py` - New. `--conversation-id` (required), `--corpus-dir`/`--justices-csv` (optional, fail-fast validated), `--out` (optional). Read-only; classification decision order is FORBIDDEN_FIELDS -> extractor-output-with-no-column (schema-absent) -> ORM-column-with-no-raw-source (upstream-missing data) -> everything else (PROPOSED, never a final "real defect").
- `pipeline/tests/test_diff_corpus_fixture.py` - New. 9 tests, self-contained (own `_write_corpus_fixture`/`isolated_session`/`_make_session_cm`, matching `test_delete_fixture_argument.py`'s established per-module pattern rather than importing another test module's helpers).
- `.planning/CORPUS-FIDELITY-DIFF.md` - New. Generator output plus narrative sections (Status, Review Gate, Out of Scope, Consumers). Regenerable via the command line in its own "Regenerating this evidence" section.
- `pipeline/corpus/loader.py` - Added `CASES_FILENAME`/`CONVERSATIONS_FILENAME`/`SPEAKERS_FILENAME`/`UTTERANCES_FILENAME` constants (no behavior change to existing functions).

## Decisions Made

- Added the four corpus filename constants to `pipeline/corpus/loader.py` (Rule 3 auto-fix: a blocking issue, not a scope choice) -- the plan's own acceptance criterion requires zero literal mentions of the four raw corpus filenames anywhere in `scripts/diff_corpus_fixture.py` outside the loader module, and the only way to satisfy that without hand-rolling a second copy of the same four names (exactly the "two sources of truth" failure mode `42-RESEARCH.md`'s Don't-Hand-Roll table warns against) was to lift them into the loader module as the single source of truth.
- The court_tenures section's "no covering tenure" branch checks for a same-last_name `is_justice=True` Person elsewhere in the database with a covering tenure BEFORE falling back to the bench-classification-timing-anomaly explanation -- this is what let the diff correctly separate the newly-discovered Person-dedup finding from Marshall's already-documented timing anomaly instead of reporting all 5 non-covering participants identically.
- All descriptive prose naming which raw file backs a field (e.g. "speakers.json speaker type") was rephrased to file-agnostic language (e.g. "speaker registry entry type") to satisfy the acceptance grep literally, which strips comment lines but not docstring/string-literal content -- the four raw filenames needed to be absent from the whole script text, not just from path-construction code.

## Deviations from Plan

**1. [Rule 3 - Blocking] Added four filename constants to pipeline/corpus/loader.py**
- **Found during:** Task 1
- **Issue:** The plan's acceptance criteria require `grep -cE 'conversations\.json|cases\.jsonl|speakers\.json|utterances\.jsonl' scripts/diff_corpus_fixture.py` (comments stripped) to equal 0, but every one of `load_cases`/`load_conversation_by_id`/`load_speakers`/`stream_utterances_for_conversation_ids` requires the caller to construct and pass an explicit `Path`, and no reusable path-resolution helper for the four corpus files existed anywhere in the codebase.
- **Fix:** Added four named string constants (`CASES_FILENAME` etc.) to `pipeline/corpus/loader.py` and imported them into the diff script instead of hardcoding the literal filenames a second time.
- **Files modified:** `pipeline/corpus/loader.py`, `scripts/diff_corpus_fixture.py`
- **Verification:** `pipeline/tests/test_corpus_loader.py` still green (9 passed, unchanged); acceptance grep now returns 0.
- **Committed in:** `51e4320d` (Task 1 commit)

**2. [Rule 1 - Bug] Windows console UnicodeEncodeError on em-dash/⏎ characters**
- **Found during:** Task 1, first real-DB run
- **Issue:** `print(document)` on the Windows `.venv` terminal (cp1252 codepage) raised `UnicodeEncodeError` on the em-dash (U+2014) and the `⏎` newline-substitution marker used throughout the script's own strings.
- **Fix:** Replaced every em-dash with plain ASCII `--` and the `⏎` marker with the ASCII string `<NL>` throughout the script.
- **Files modified:** `scripts/diff_corpus_fixture.py`
- **Verification:** Re-ran against the real fixture on the same Windows terminal; no encoding error.
- **Committed in:** `51e4320d` (Task 1 commit)

**3. [Rule 1 - Bug] `sys.path.insert(0, ...)` false-triggered the read-only-script write-verb grep**
- **Found during:** Task 1, acceptance-criteria check
- **Issue:** The plan's acceptance grep `\bdelete\(|\bupdate\(|\binsert\(|session\.add` (intended to prove the script issues no writes) also matches `sys.path.insert(0, ...)`'s `insert(` substring -- a false positive on an unrelated, necessary import-path bootstrap line.
- **Fix:** Replaced `sys.path.insert(0, str(ROOT))` with the equivalent `sys.path[0:0] = [str(ROOT)]` slice assignment.
- **Files modified:** `scripts/diff_corpus_fixture.py`
- **Verification:** Grep now returns 0; script still imports and runs correctly.
- **Committed in:** `51e4320d` (Task 1 commit)

---

**Total deviations:** 3 auto-fixed (1 blocking/Rule 3, 2 bug/Rule 1).
**Impact on plan:** All three were necessary to satisfy the plan's own literal acceptance criteria and to run correctly in this project's documented Windows-terminal environment; none changed the script's design, scope, or the classification logic the plan specified.

## Issues Encountered

None beyond the deviations above. The environment worked as documented on the first attempt (real dev DB + real `data/corpus/` from the Windows `.venv`).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `.planning/CORPUS-FIDELITY-DIFF.md`'s Review Gate section (8 numbered items) is ready for Plan 04's checkpoint to present verbatim to the operator for the single-batch review (D-05/D-06):
  1. `Utterance.section_hint` never populated -- proposed real defect (Pitfall 3).
  2. Marshall's bench-classification timing anomaly, nine months before his real tenure begins (Pitfall 2) -- three fix options presented.
  3. `url`/`adv_sides_inferred`/`known_respondent_adv`/per-advocate `role` dropped before the allowlist -- proposed schema-absent/low-urgency.
  4. ConvoKit's per-turn `id`/`meta.start_times`/`meta.stop_times`/`meta.timestamp`/`reply_to` dropped -- proposed schema-absent.
  5. `extract_conversation_fields`'s dead `conversation_id` key -- proposed documentation/cleanup note.
  6. `is_eq_divided` outcome-adjacent but not in `FORBIDDEN_FIELDS` -- proposed documentation-completeness note.
  7. court_tenures integrity findings flagged-not-fixed (D-03), owner named as `import_justices_csv.py`.
  8. **New finding:** Person-dedup mismatch between the corpus importer and `import_justices_csv.py` for White/Black/Clark/Douglas -- proposed real defect candidate (Person dedup should try a name-normalization match before creating a new row).
- The generator (`scripts/diff_corpus_fixture.py`) is proven regenerable and is exactly the instrument Plan 05 re-runs post-fix to prove each approved fix landed without assuming it worked.
- No blockers. `pipeline/tests/` fully green (216 passed, 5 pre-existing xfailed, unrelated). Zero database writes made by this plan (`arguments` count for the fixture unchanged at 1).

---
*Phase: 42-corpus-import-fidelity-diff-fix*
*Completed: 2026-07-30*

## Self-Check: PASSED

- FOUND: scripts/diff_corpus_fixture.py
- FOUND: pipeline/tests/test_diff_corpus_fixture.py
- FOUND: .planning/CORPUS-FIDELITY-DIFF.md
- FOUND: pipeline/corpus/loader.py
- FOUND: .planning/phases/42-corpus-import-fidelity-diff-fix/42-03-SUMMARY.md
- FOUND commit: 51e4320d (Task 1)
- FOUND commit: 4b649d98 (Task 2)
- FOUND commit: bb62cfd3 (Task 3)
