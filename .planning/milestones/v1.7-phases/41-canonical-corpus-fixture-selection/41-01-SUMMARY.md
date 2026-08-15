---
phase: 41-canonical-corpus-fixture-selection
plan: 01
subsystem: pipeline
tags: [convokit, corpus-analysis, offline-script, apolitical-constraint, fixture-selection]

# Dependency graph
requires: []
provides:
  - "scripts/select_corpus_fixtures.py: offline path-coverage scoring script over the local ConvoKit corpus"
  - "Deterministic top-5 complexity shortlist + recommendation, printed to stdout"
  - "3 proposed state-variety fixture candidates (target labels, not corpus-discovered states)"
  - "Paste-ready 4-row fixtures-draft table for .planning/FIXTURES.md"
  - "Persistable full-corpus aggregate cache (data/corpus/fixture_scan_cache.json, gitignored)"
affects: [42-corpus-import-fidelity-diff-and-fix, 43-dev-only-reset-to-fixture]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Path-coverage checklist scoring (4 independent boolean flags, ranked by coverage breadth then magnitude then id) instead of a weighted composite score"
    - "Apolitical hard exclusion enforced 3 ways: structurally (only extract_case_fields/extract_conversation_fields reach raw corpus dicts), at runtime (--self-check check 4), and at commit-time-equivalent (a FORBIDDEN_FIELDS literal-hit grep run as a verify gate)"
    - "Streaming-pass aggregate cache (schema_version + complete + rows_scanned + aggregates) so a 900MB file is streamed once and re-ranked at any threshold without re-streaming"

key-files:
  created:
    - scripts/select_corpus_fixtures.py
  modified: []

key-decisions:
  - "Recommendation flipped from RESEARCH.md's provisional pick once run against the FULL corpus: conversation 15169 (Baltimore & Ohio Railroad Co. v. United States, docket 642, 1966 term) is the actual top-ranked candidate at 3/4 coverage, not 14837 (Permian Basin) as RESEARCH.md's partial/exploratory run suggested. 14837 clears only 2/4 (misses high_speaker_dedup) once real distinct-speaker counts are streamed from the full utterances.jsonl. 14969 (Shapiro v. Thompson) ties 15169 at 3/4 and is named as the runner-up. This is exactly the operator-confirmation point the phase is built around (RESEARCH A1) -- Plan 03's checkpoint is where the operator picks between them."
  - "State-variety header text deliberately reads 'Target Role' (not 'Role') so it is textually distinct from the Fixtures Draft table's fixed 'Role' header -- prevents a naive substring scan over the whole report from latching onto the wrong table."
  - "Fixtures-draft Role-cell capitalization: labels already carrying meaningful embedded capitalization (the 'DRAFT' acronym) print verbatim; plain-word labels get a leading capital for display consistency. Avoids partially mutating an acronym mid-word."

patterns-established:
  - "One-off analysis/audit scripts under scripts/ follow audit_tenure_seat_identifiers.py's skeleton: shebang, spec-as-docstring citing decision IDs, ROOT = Path(__file__).resolve().parent.parent, main() -> int, if __name__ == '__main__': raise SystemExit(main())"

requirements-completed: [CORPUS-12]

coverage:
  - id: D1
    description: "Bounded end-to-end pass: corpus resolution, allowlisted loads, one streaming aggregation, case-id join, four-flag scoring, deterministic top-5 shortlist printout"
    requirement: "CORPUS-12"
    verification:
      - kind: other
        ref: "python3 scripts/select_corpus_fixtures.py --max-utterance-rows 50000 (5-row shortlist, each N/4 coverage)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Corpus-free --self-check harness proving total-order, degenerate-input, zero-coverage, and apolitical-containment properties"
    requirement: "CORPUS-12"
    verification:
      - kind: other
        ref: "python3 scripts/select_corpus_fixtures.py --self-check (4/4 PASS lines)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Fail-fast corpus-dir/file resolution naming all four required filenames, no traceback"
    requirement: "CORPUS-12"
    verification:
      - kind: other
        ref: "python3 scripts/select_corpus_fixtures.py --corpus-dir /nonexistent-corpus-dir (exit 1, names all 4 files)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Apolitical exclusion: FORBIDDEN_FIELDS literal names never appear in the script's source text"
    requirement: "CORPUS-12"
    verification:
      - kind: other
        ref: "python3 -c \"... FORBIDDEN_FIELDS intersection with source text ...\" (forbidden_literal_hits=none)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Persistable full-corpus mode: --cache-out writes a schema-versioned aggregate cache; --cache re-ranks from it without re-streaming; --allow-partial gates incomplete caches"
    requirement: "CORPUS-12"
    verification:
      - kind: other
        ref: "python3 scripts/select_corpus_fixtures.py --max-utterance-rows 20000 --cache-out ... (complete=false, aggregates=7817); ranking without --allow-partial exits 1 naming allow-partial"
        status: pass
    human_judgment: false
  - id: D6
    description: "Determinism: two consecutive runs over the same cache produce byte-identical stdout"
    requirement: "CORPUS-12"
    verification:
      - kind: other
        ref: "diff of two consecutive --cache runs (both partial-cache and full-cache)"
        status: pass
    human_judgment: false
  - id: D7
    description: "Report sections: signal distributions, recommendation naming every tied runner-up, 3 state-variety proposals, paste-ready 4-row fixtures-draft table"
    requirement: "CORPUS-12"
    verification:
      - kind: other
        ref: "python3 scripts/select_corpus_fixtures.py --cache data/corpus/fixture_scan_cache.json (full unbounded report, all sections present)"
        status: pass
    human_judgment: false
  - id: D8
    description: "Scope guard: no importer/API/DB file and no corpus source file modified this plan"
    requirement: "CORPUS-12"
    verification:
      - kind: other
        ref: "git status --porcelain -- api pipeline alembic app data/corpus/*.jsonl data/corpus/*.json (empty)"
        status: pass
    human_judgment: false

duration: 2h32m (includes an operator-verification pause between Task 1 and Task 2)
completed: 2026-07-29
status: complete
---

# Phase 41 Plan 01: Path-Coverage Corpus Fixture Scoring Script Summary

**Offline `scripts/select_corpus_fixtures.py` streams the full 1.7M-row ConvoKit utterances corpus once, scores all 7,817 conversations on a 4-flag path-coverage checklist (never a weighted sum), and prints a deterministic top-5 shortlist, recommendation, 3 state-variety proposals, and a paste-ready fixtures-draft table — with the apolitical field exclusion enforced structurally, at runtime, and via a commit-gate-equivalent literal-hit check.**

## Performance

- **Duration:** 2h32m wall clock (Task 1 commit to Task 2 commit); includes an operator human-verify checkpoint pause between tasks, not continuous active work
- **Started:** 2026-07-29T14:25:44-05:00 (first commit read from git log)
- **Completed:** 2026-07-29T17:16:48-05:00
- **Tasks:** 2 (Task 1: tracer, Task 2: expansion)
- **Files modified:** 1 (`scripts/select_corpus_fixtures.py`, created)

## Accomplishments

- Built `scripts/select_corpus_fixtures.py`: a single script covering the whole analysis path end to end — corpus resolution, allowlisted reads via `pipeline.corpus.apolitical`, one streaming pass over `utterances.jsonl` via `pipeline.corpus.loader`, case-id join (never `docket_no`), four-flag path-coverage scoring, and a deterministic ranked printout.
- Ran the script against the real, full local corpus (`data/corpus/`, 7,748 cases / 7,817 conversations / 9,651 speakers / 1,700,789 utterance rows) and confirmed the real top-5 shortlist, recommendation, and 3-fixture state-variety table all render correctly and deterministically.
- Persisted a full-corpus aggregate cache (`data/corpus/fixture_scan_cache.json`, gitignored derived data) so Plan 02/03 (or a re-run) never need to re-stream the 900MB file to re-rank at a different threshold.
- Corpus-free `--self-check` harness proves 4 properties without touching any corpus file: total ordering (including a coverage tie and a nested magnitude-sum tie), degenerate inputs (empty/single/over-request), zero-coverage behavior, and apolitical containment (the extractors' own returned key set never intersects `FORBIDDEN_FIELDS`, derived from the imported frozenset rather than hardcoded).
- The apolitical exclusion (D-04) is verified 3 independent ways: structurally (only `extract_case_fields`/`extract_conversation_fields` ever touch a raw corpus dict), at runtime (`--self-check` check 4), and via a literal-hit grep of `FORBIDDEN_FIELDS` names against the script's own source text (0 hits).

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end path-coverage scoring — one bounded pass, ranked shortlist out** - `ac4b877b` (feat)
2. **Task 2: Expand to persistable full-corpus mode, tunable thresholds, and the operator-facing report sections** - `a510f186` (feat)

_Between Task 1 and Task 2, a `checkpoint:human-verify` was returned per the tracer-feedback-gate protocol (this project's `workflow.auto_advance` is `false`). The operator ran the tracer's verification commands independently and approved proceeding with Task 2._

## Files Created/Modified

- `scripts/select_corpus_fixtures.py` - Offline path-coverage scoring script over the local ConvoKit corpus; produces the ranked complexity shortlist, recommendation, state-variety proposals, and fixtures-draft table this phase's operator-confirmation step (Plan 03) and `.planning/FIXTURES.md` (Plan 02) consume.

## Decisions Made

- **Recommendation changed from RESEARCH.md's exploratory finding once run against the full corpus.** RESEARCH.md's own research-session run (also against the real corpus, but computed slightly differently during discovery) suggested conversation `14837` (Permian Basin Area Rate Cases) as the top pick. This plan's script, run against the complete, correctly-joined corpus, finds conversation `15169` (Baltimore & Ohio Railroad Co. v. United States, docket 642, 1966 term) at 3/4 coverage as the actual top-ranked candidate — `14837` clears only 2/4 (advocate + reargument, missing the high-speaker-dedup flag) once real per-conversation distinct-speaker counts are streamed. Conversation `14969` (Shapiro v. Thompson) ties `15169` at 3/4 and is named as the runner-up. This does not require any code fix — it's exactly the "coverage tie is the operator's call" scenario RESEARCH A1 anticipated, and Plan 03's blocking `checkpoint:decision` is where the operator confirms the pick. Recording it here so the discrepancy with RESEARCH.md's earlier number isn't mistaken for a bug later.
- **State-variety table header uses "Target Role" instead of "Role"** so it's textually distinct from the Fixtures Draft table's fixed `| Role | Conversation ID | ...` header — avoids a naive substring/sed scan over the full report accidentally selecting the wrong table.
- **Fixtures-draft Role-cell capitalization rule:** a role label that already carries meaningful embedded capitalization (the state-variety proposal's `unpublished/DRAFT target`) is printed verbatim rather than force-capitalized, which would only touch the leading character and risk an inconsistent mixed-case result; plain-word labels (`published target`, `mid-pipeline target`) get a leading capital letter for display consistency with the literal `Complexity fixture` label.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] State-variety and fixtures-draft table headers collided under a substring scan**
- **Found during:** Task 2 (own verify command for the fixtures-draft table row count)
- **Issue:** The initial implementation gave the state-variety proposals table the same `| Role | Conversation ID | ...` header prefix as the Fixtures Draft table. A line-range scan anchored on that header text (as the plan's own verify command does) selected both tables at once instead of just the intended one, producing an incorrect row count.
- **Fix:** Renamed the state-variety table's header to lead with `Target Role` instead of `Role`, keeping all other columns and semantics unchanged.
- **Files modified:** `scripts/select_corpus_fixtures.py`
- **Verification:** Re-ran the fixtures-draft verify command; it now selects exactly the intended table and counts the correct 4 data rows.
- **Committed in:** `a510f186` (Task 2 commit)

**2. [Rule 3 - Blocking] First manual full-corpus verification run raced with itself and corrupted the cache file**
- **Found during:** post-Task-2 manual sanity check (not a plan-required verify step)
- **Issue:** An initial attempt to launch the full unbounded streaming pass in the background used a shell `&` inside a foreground tool call; when a second, correctly-launched background run was started against the same output path shortly after, both processes wrote to `data/corpus/fixture_scan_cache.json` concurrently, corrupting the JSON (malformed at a mid-file offset).
- **Fix:** Confirmed no stray process remained, deleted the corrupted cache file, and re-ran the full streaming pass exactly once via the tool's proper background-execution mechanism. The resulting cache parses cleanly (`complete=true`, `rows_scanned=1700789`, 7817 aggregate entries) and two consecutive `--cache`-based runs are byte-identical.
- **Files modified:** none (only regenerated the gitignored derived-data cache file; `data/corpus/fixture_scan_cache.json` is never committed)
- **Verification:** `python3 -c "json.load(...)"` succeeds; `--cache ... ` run twice diffs identical.
- **Committed in:** N/A (no source change; cache file is gitignored, not a git artifact)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking/operational)
**Impact on plan:** Both fixes are self-contained to this plan's own script/verification and required no scope changes. No importer, API, or database file was touched at any point (confirmed via the scope-guard verify command after every task and after the full-corpus run).

## Issues Encountered

None beyond the two auto-fixed deviations above.

## User Setup Required

None - no external service configuration required. The script requires only the operator-supplied, gitignored ConvoKit corpus files already present in `data/corpus/` (confirmed present: `cases.jsonl`, `conversations.json`, `speakers.json`, `utterances.jsonl`).

## Next Phase Readiness

- `scripts/select_corpus_fixtures.py` is committed, runs end to end under a bare `python3` (no new dependency; falls back to a regex date parser when `dateutil` is unavailable), and its full-corpus run is confirmed correct and deterministic.
- The real full-corpus recommendation is conversation `15169` (Baltimore & Ohio Railroad Co. v. United States), with `14969` (Shapiro v. Thompson) as the named 3/4-coverage runner-up — Plan 02 should transcribe from this plan's actual full-corpus stdout (or re-run `python3 scripts/select_corpus_fixtures.py --cache data/corpus/fixture_scan_cache.json`) rather than from RESEARCH.md's earlier exploratory number, which this plan's more complete run supersedes.
- Plan 02 can read directly from the persisted `data/corpus/fixture_scan_cache.json` (full, complete cache already generated) to build `.planning/FIXTURES.md` without re-streaming the 900MB file.
- Plan 03's operator-confirmation checkpoint has real tie information to present: `15169` vs. `14969` at equal 3/4 coverage, plus the 3 state-variety candidates (`13015`, `18897`, `22372`), all already present in this script's own recommendation and fixtures-draft output.
- No blockers.

---
*Phase: 41-canonical-corpus-fixture-selection*
*Completed: 2026-07-29*
