---
phase: 41-canonical-corpus-fixture-selection
plan: 02
subsystem: infra
tags: [convokit, corpus-analysis, planning-doc, apolitical-constraint, fixture-selection]

# Dependency graph
requires:
  - phase: 41-canonical-corpus-fixture-selection (Plan 01)
    provides: "scripts/select_corpus_fixtures.py and the persisted, complete full-corpus aggregate cache (data/corpus/fixture_scan_cache.json)"
provides:
  - ".planning/FIXTURES.md: the PROPOSED four-fixture record (project root) — complexity fixture + 3 state-variety targets, ranked shortlist evidence, recommendation with named tied runner-up, signal/threshold definitions, regeneration command, consumer map"
affects: [41-03-operator-confirmation, 42-corpus-import-fidelity-diff-and-fix, 43-dev-only-reset-to-fixture, 45-deferred-ui-bug-fixes]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Planning-doc section ordering chosen to satisfy grep-anchored automated verify gates (evidence/methodology tables before the final uniform fixture table) rather than the plan's prose-listed order, since a table's own literal header line unavoidably matches the same '^| [A-Z]' probe used to bound the fixture table's row count"

key-files:
  created:
    - .planning/FIXTURES.md
  modified: []

key-decisions:
  - "Recommendation transcribed verbatim from the real full-corpus cached re-rank: conversation 15169 (Baltimore & Ohio Railroad Company v. United States, docket 642, 1966 term) at 3/4 coverage, with conversation 14969 (Shapiro v. Thompson) as the named tied runner-up. This supersedes RESEARCH.md's earlier exploratory pick of conversation 14837 (Permian Basin Area Rate Cases), which does not appear in the real top-5 at all -- it clears only 2/4 flags (misses high_speaker_dedup) once real full-corpus distinct-speaker counts are streamed."
  - "Section order in FIXTURES.md deviates from the plan's literal prose listing (Status, Fixture Set, Why-ranked, Ranked Shortlist, Signal Definitions, State-variety, Regenerating, Consumers) -- moved Ranked Shortlist and Signal Definitions ahead of Fixture Set. The plan's own gate-2 verify command counts '^| [A-Z]' lines from the Fixture-Set header to EOF and requires exactly 4; the plan's own gate-3 verify command requires a literal '| Rank ' table header to exist. Under the plan's literal prescribed order, the mandatory Ranked-Shortlist header (which itself matches '^| [A-Z]') would always land after the Fixture-Set anchor and push the gate-2 count to 5, an unsatisfiable combination. Reordering (methodology/evidence before the final proposed table) preserves every mandated section, heading, and content requirement while making both grep-anchored gates arithmetically satisfiable."
  - "Transcribed the unpublished/DRAFT target role label in lowercase ('unpublished/DRAFT') exactly as scripts/select_corpus_fixtures.py's own report prints it, rather than the plan prose's title-cased 'Unpublished/DRAFT target' -- the plan's own action text mandates verbatim transcription from the captured report and gate 2's corresponding grep check is case-insensitive (-qi), so verbatim transcription and gate-passing both point to the lowercase form."

patterns-established: []

requirements-completed: [CORPUS-12]

coverage:
  - id: D1
    description: "Full-corpus streaming pass persisted and re-rank produces the real ranked report (already complete from Plan 01's cache; re-verified complete=true, rows_scanned=1700789, aggregates=7817=len(conversations.json))"
    requirement: "CORPUS-12"
    verification:
      - kind: other
        ref: "python3 -c \"... complete is True and rows_scanned>=1700000 and len(aggregates)==len(conversations) ...\" (exit 0)"
        status: pass
      - kind: other
        ref: "python3 scripts/select_corpus_fixtures.py --cache data/corpus/fixture_scan_cache.json (5-row shortlist + 4-row fixture table printed)"
        status: pass
    human_judgment: false
  - id: D2
    description: ".planning/FIXTURES.md exists at project root (not phase-nested) at Status: PROPOSED, with the uniform four-row fixture table, ranked shortlist evidence, recommendation + named tied runner-up, signal/threshold definitions, Phase 43 target-label caveat, regeneration command, and consumer map"
    requirement: "CORPUS-12"
    verification:
      - kind: other
        ref: "LOCATION_AND_STATUS_OK / FIXTURE_TABLE_OK (fixture_rows=4) / SHORTLIST_EVIDENCE_OK (shortlist_rows=5) / TIES_REGEN_CONSUMERS_OK verify gates, all pass"
        status: pass
    human_judgment: false
  - id: D3
    description: "Zero apolitical FORBIDDEN_FIELDS literal hits in FIXTURES.md; scope guard confirms no api/pipeline/alembic/app/data-corpus file changed"
    requirement: "CORPUS-12"
    verification:
      - kind: other
        ref: "python3 -c \"... FORBIDDEN_FIELDS intersection with FIXTURES.md text ...\" (forbidden_literal_hits=none); git status --porcelain -- api pipeline alembic app data/corpus (empty)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Human-check: Fixture Set table's four rows share one uniform shape differing only in the Role cell, and no fixture's outcome/holding/vote/political-significance appears anywhere in the document"
    verification: []
    human_judgment: true
    rationale: "The apolitical prose prohibition (no outcome/holding/political-significance commentary) cannot be proven by grep alone -- a human must read the Fixture Set table and recommendation section to confirm no such commentary crept in, per this task's own <human-check> verify step."

duration: 9min
completed: 2026-07-29
status: complete
---

# Phase 41 Plan 02: Author FIXTURES.md as the PROPOSED Four-Fixture Record Summary

**`.planning/FIXTURES.md` created at the project root, transcribed verbatim from the real full-corpus re-rank of `scripts/select_corpus_fixtures.py`: conversation 15169 (Baltimore & Ohio Railroad Co. v. United States) recommended as the complexity fixture at 3/4 path coverage, with 14969 (Shapiro v. Thompson) as the named tied runner-up, alongside three state-variety target fixtures (13015, 18897, 22372) -- Status: PROPOSED, awaiting Plan 03's operator confirmation.**

## Performance

- **Duration:** 9 min wall clock (the expensive full-corpus streaming pass was already run and persisted by Plan 01; this plan only re-ranked from the cache and authored the document)
- **Started:** 2026-07-29T22:40:04Z
- **Completed:** 2026-07-29T22:49:12Z
- **Tasks:** 2 (Task 1: re-rank from persisted cache and reconcile; Task 2: author FIXTURES.md)
- **Files modified:** 1 (`.planning/FIXTURES.md`, created)

## Accomplishments

- Confirmed Plan 01's persisted `data/corpus/fixture_scan_cache.json` is complete (`complete=true`, `rows_scanned=1700789`, 7817 aggregate entries matching `conversations.json`'s own 7817 conversations) -- no re-streaming of the 900MB source file was needed.
- Re-ran `scripts/select_corpus_fixtures.py --cache data/corpus/fixture_scan_cache.json` and captured its full report: signal distributions, top-5 ranked shortlist, recommendation, state-variety proposals, and paste-ready fixtures-draft table.
- Reconciled this run's real output against RESEARCH.md's earlier exploratory expectation: RESEARCH.md expected conversation 14837 (Permian Basin) to lead with 15169/14852/14969 tied. The real full-corpus run instead ranks 15169 first (3/4 coverage) with 14969 tied as the sole runner-up at that coverage level; 14837 does not appear in the top 5 at all (clears only 2/4, missing `high_speaker_dedup`), and 14852 also clears only 2/4 (missing `multi_advocate_resolution`) in this run. Documented the divergence and its cause explicitly in `FIXTURES.md`'s "Why the complexity fixture ranked first" section.
- Authored `.planning/FIXTURES.md` at the project root (not phase-nested) at `Status: PROPOSED`: the uniform four-row Fixture Set table (Complexity fixture / unpublished-DRAFT target / Published target / Mid-pipeline target, all sharing one shape), the 5-row Ranked Shortlist evidence table with all four flag identifiers, the signal/threshold definitions naming the apolitical allowlist module, the recommendation with its named tied runner-up, the Phase 43 target-label caveat (state variety is a target for Phase 43 to realize, not a corpus-discovered property), the exact two-command regeneration recipe, and the Phase 42/43/45 consumer map.
- Verified zero `pipeline.corpus.apolitical.FORBIDDEN_FIELDS` literal hits anywhere in the document, and confirmed no file under `api/`, `pipeline/`, `alembic/`, `app/`, or `data/corpus/` changed.

## Task Commits

Each task was committed atomically:

1. **Task 1: Full-corpus streaming pass, persisted, then the real ranked report** - no commit (read-only re-verification against Plan 01's already-committed-as-gitignored cache; nothing new to stage). Cache confirmed complete via automated checks; report captured to a scratchpad file for transcription.
2. **Task 2: Author .planning/FIXTURES.md as the PROPOSED four-fixture record** - `a9f0551c` (docs)

## Files Created/Modified

- `.planning/FIXTURES.md` - The PROPOSED four-fixture record: ranked shortlist evidence, signal/threshold definitions, uniform four-row fixture table, recommendation with named tied runner-up, Phase 43 target-label caveat, regeneration command, and consumer map. Sole handoff artifact for Phase 42 (complexity fixture row only) and Phase 43 (all four rows).

## Decisions Made

- **Recommendation is 15169, superseding RESEARCH.md's 14837.** Task 1's report (the authoritative, full-corpus, complete-cache result) ranks conversation 15169 (Baltimore & Ohio Railroad Co. v. United States) first at 3/4 coverage, with 14969 (Shapiro v. Thompson) as the sole tied runner-up at that coverage. This matches Plan 01's own finding and is exactly the "coverage tie is the operator's call" scenario RESEARCH A1 anticipated -- Plan 03's confirmation checkpoint is where the operator picks between 15169 and 14969, or redirects entirely.
- **FIXTURES.md section order deviates from the plan's literal prose listing** (see key-decisions in frontmatter for the full mechanical reasoning): Ranked Shortlist (evidence) and Signal definitions and thresholds now appear before Fixture Set, rather than after. This was required because the plan's own gate-2 verify command (`sed -n '/^| Role | Conversation ID /,$p' | grep -c '^| [A-Z]'` must equal 4) and gate-3 verify command (requires a literal `| Rank ` header to exist) are jointly unsatisfiable under the plan's literally prescribed order -- the mandatory Ranked-Shortlist table header itself always matches the same `^| [A-Z]` probe gate 2 uses to count the Fixture Set table's rows, so if it appears after Fixture Set (per the prescribed order), gate 2's count becomes 5, not 4. Reordering these sections (pure presentation change, zero content loss, every mandated heading and requirement still present) resolves the conflict. All acceptance criteria and human-check content requirements are unaffected by this reordering.
- **Transcribed `unpublished/DRAFT target` in lowercase**, matching the script's own printed capitalization exactly (rather than the plan prose's title-cased "Unpublished/DRAFT target"), per the action text's "do not round, reformat, or tidy" verbatim-transcription instruction. Gate 2's corresponding check uses case-insensitive grep (`-qi`), so this choice satisfies both the transcription fidelity requirement and the gate.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Plan's own gate-2 and gate-3 verify commands were jointly unsatisfiable under the plan's literally prescribed section order**
- **Found during:** Task 2 (authoring `.planning/FIXTURES.md`, running its own verify commands)
- **Issue:** Gate 2 counts lines matching `^| [A-Z]` from the Fixture Set table's header to end-of-file and requires exactly 4. Gate 3 requires a literal `| Rank ` table header to exist somewhere in the document (for the Ranked Shortlist section, mandated by the same task). Since a markdown table header beginning with "Rank" (capital R) also matches gate 2's `^| [A-Z]` probe, placing Ranked Shortlist after Fixture Set (as the plan's prose section order literally lists) makes gate 2's count 5 or more, never exactly 4 -- an unsatisfiable combination given both gates must pass and all mandated sections/headings must be present verbatim.
- **Fix:** Reordered sections so Ranked Shortlist (evidence) and Signal definitions and thresholds appear before Fixture Set, and confirmed no table header appears after the Fixture Set anchor for the remainder of the document. Every mandated section, heading text, and required content (four-row uniform table, 5-row shortlist, all four flag names, recommendation, runners-up, Phase 43 caveat, regeneration command, consumer map) is fully present -- only the section ordering changed.
- **Files modified:** `.planning/FIXTURES.md` (authored directly with the corrected order; no separate re-fix commit needed since this was caught before the initial commit)
- **Verification:** Re-ran all of Task 2's automated verify gates after reordering; all six gates (`LOCATION_AND_STATUS_OK`, `FIXTURE_TABLE_OK` with `fixture_rows=4`, `SHORTLIST_EVIDENCE_OK` with `shortlist_rows=5`, `TIES_REGEN_CONSUMERS_OK`, the `FORBIDDEN_FIELDS` zero-hits check, and the `SCOPE_GUARD_OK` git-status check) now pass.
- **Committed in:** `a9f0551c` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking/verify-script conflict)
**Impact on plan:** Presentation-only change (section order); zero content, data, or scope impact. No importer, API, or database file touched at any point (confirmed via the scope-guard verify command).

## Issues Encountered

None beyond the one auto-fixed deviation above.

## User Setup Required

None - no external service configuration required. This plan only reads the already-present, gitignored `data/corpus/` files and Plan 01's persisted cache.

## Next Phase Readiness

- `.planning/FIXTURES.md` is committed at the project root, `Status: PROPOSED`, with the full four-fixture record (complexity fixture 15169, tied runner-up 14969, and the three state-variety targets 13015/18897/22372) and all required D-08 fields populated for every row.
- Plan 03's operator-confirmation checkpoint has everything it needs: the 3/4-coverage tie between conversation 15169 and 14969, the three state-variety candidates, and the exact regeneration command if the operator wants to re-verify or re-run against an updated corpus snapshot before confirming.
- No blockers.

---
*Phase: 41-canonical-corpus-fixture-selection*
*Completed: 2026-07-29*
