---
phase: 41-canonical-corpus-fixture-selection
verified: 2026-07-29T18:20:00Z
status: passed
score: 6/6 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 41: Canonical Corpus Fixture Selection Verification Report

**Phase Goal:** Canonical Corpus & Fixture Selection — score the local ConvoKit corpus for import-path coverage, propose a four-fixture set (one complexity fixture + three state-variety targets), and get explicit operator confirmation before any downstream phase treats it as final.
**Verified:** 2026-07-29T18:20:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A ranked shortlist of candidate arguments from the full ConvoKit dataset is presented with concrete structural signals per candidate | ✓ VERIFIED | `python3 scripts/select_corpus_fixtures.py --cache data/corpus/fixture_scan_cache.json` (re-run live) prints a 5-row shortlist with Advocates/Distinct Speakers/Bench Speakers/Turns/Transcripts/Flags-hit columns, byte-identical to `.planning/FIXTURES.md`'s "Ranked Shortlist (evidence)" table. `--self-check` passes 4/4 PASS lines (ordering, degenerate inputs, zero-coverage, apolitical containment). |
| 2 | Exactly one argument recommended as complexity fixture with a stated path-coverage reason, plus 3 state-variety proposals | ✓ VERIFIED | Live full-cache run recommends conversation 15169 (3/4 coverage: multi_advocate_resolution, high_speaker_dedup, reargument_question_number), names 14969 as the sole tied runner-up, and prints the 3 state-variety proposals (13015, 18897, 22372) with the D-08 fields. Matches FIXTURES.md exactly. |
| 3 | Operator explicitly confirms (or rejects/redirects) the full 4-fixture recommendation before downstream work begins | ✓ VERIFIED | `.planning/FIXTURES.md` line 5: `Status: CONFIRMED (2026-07-29)`. `## Confirmation` section (lines 7-13) records the operator's verbatim decision ("Operator selected option 1: confirm-as-proposed... no substitutions"), sourced from a blocking `checkpoint:decision` task (`autonomous: false` in 41-03-PLAN.md frontmatter), not an inferred/auto-approved result. |
| 4 | Confirmed fixture set recorded in a durable, referenceable form (conversation id, case name, docket(s), term, argued date, role) that Phase 42/43 read instead of re-deriving | ✓ VERIFIED | `.planning/FIXTURES.md` § "Fixture Set" holds one 4-row table, all 5 D-08 fields populated on every row, no placeholder cells (`sed`/grep check: fixture_rows=4). § "Consumers" explicitly states Phase 42 reads the Complexity fixture row only, Phase 43 reads all four, Phase 45 reads Published/unpublished-DRAFT rows. |
| 5 | No importer code and no database rows are changed by this phase | ✓ VERIFIED | `git status --porcelain -- api pipeline alembic app data/corpus` returns empty. `git diff --stat ac4b877b~1..20877cca` across the full phase commit range touches only `.planning/FIXTURES.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/STATE.md`, phase SUMMARY files, and `scripts/select_corpus_fixtures.py` — no file under `api/`, `pipeline/`, `alembic/`, or `app/`. |
| 6 | Apolitical hard constraint holds — no outcome/SCDB-derived field reachable in the scoring code or the durable record | ✓ VERIFIED | Live re-run of the literal-hit check: `FORBIDDEN_FIELDS` intersection with `scripts/select_corpus_fixtures.py` source = none; intersection with `.planning/FIXTURES.md` text = none. `--self-check`'s apolitical-containment check also passes. |

**Score:** 6/6 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `scripts/select_corpus_fixtures.py` | Offline read-only scoring script, importer/DB untouched | ✓ VERIFIED | 853 lines, committed (`ac4b877b`, `a510f186`). `--self-check` exits 0. Full-cache run reproduces FIXTURES.md's numbers exactly. |
| `data/corpus/fixture_scan_cache.json` | Persisted full-corpus aggregate cache, gitignored | ✓ VERIFIED | Exists, `complete=true`, `rows_scanned=1700789`, `aggregates` has 7817 entries == `len(conversations.json)`. Confirmed gitignored (`git status --porcelain -- data/corpus` empty). |
| `.planning/FIXTURES.md` | Project-root planning doc, CONFIRMED, 4-fixture uniform table | ✓ VERIFIED | Exists at project root (not phase-nested). `Status: CONFIRMED`. 4-row Fixture Set table, 5-row Ranked Shortlist evidence table, recommendation + named runner-up, state-variety Phase-43-target caveat, regeneration command, consumer map, zero FORBIDDEN_FIELDS hits. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `scripts/select_corpus_fixtures.py` | `pipeline.corpus.loader` | imports `load_cases`, `load_speakers`, `stream_utterances_for_conversation_ids` | ✓ WIRED | `grep` confirms all three names present in script source; live run successfully executes end to end using these loaders. |
| `scripts/select_corpus_fixtures.py` | `pipeline.corpus.apolitical` | imports `extract_case_fields`, `extract_conversation_fields`, `FORBIDDEN_FIELDS` | ✓ WIRED | `grep` confirms presence; live containment check confirms zero literal hits and self-check confirms extractor-output containment at runtime. |
| `.planning/FIXTURES.md` fixture table | `scripts/select_corpus_fixtures.py` printed output | transcription | ✓ WIRED | Live re-run of `--cache data/corpus/fixture_scan_cache.json` produces a Fixtures Draft table byte-for-byte matching FIXTURES.md's Fixture Set table (conversation ids 15169/13015/18897/22372, same case names/dockets/terms/dates). |
| `.planning/FIXTURES.md` status/confirmation | Phase 42 / Phase 43 start gate | referenceable CONFIRMED status | ✓ WIRED | Status line reads CONFIRMED, not PROPOSED — the machine-visible signal downstream phases would check before starting. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CORPUS-12 | 41-01, 41-02, 41-03 | 4-argument fixture set identified (1 complexity + 3 state-variety), confirmed with operator before use | ✓ SATISFIED | All 6 observable truths above verified; REQUIREMENTS.md traceability table marks CORPUS-12 → Phase 41 → Complete, consistent with the confirmed FIXTURES.md and passing scoring script. |

No orphaned requirements: `grep -n "Phase 41" .planning/REQUIREMENTS.md` shows only CORPUS-12 mapped to Phase 41, matching the sole `requirements: [CORPUS-12]` declared across all three plan frontmatters.

### Anti-Patterns Found

None. `grep -n -E "TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER"` and a case-insensitive "placeholder/coming soon/not yet implemented" scan over `scripts/select_corpus_fixtures.py` and `.planning/FIXTURES.md` returned zero hits.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Self-check harness (ordering, degenerate inputs, zero-coverage, apolitical containment) | `python3 scripts/select_corpus_fixtures.py --self-check` | 4/4 `PASS` lines | ✓ PASS |
| Full-corpus cached re-rank reproduces FIXTURES.md exactly | `python3 scripts/select_corpus_fixtures.py --cache data/corpus/fixture_scan_cache.json` | Rank 1 = 15169 (3/4), runner-up 14969 (3/4), state-variety rows 13015/18897/22372 — matches FIXTURES.md verbatim | ✓ PASS |
| Determinism across two consecutive cached runs | two independent invocations, diffed | identical stdout | ✓ PASS |
| Fail-fast on missing corpus dir | `--corpus-dir /nonexistent-corpus-dir` | exit 1, stderr names cases.jsonl/conversations.json/speakers.json/utterances.jsonl, no traceback | ✓ PASS |
| Apolitical containment (literal-hit check) | `FORBIDDEN_FIELDS` intersection against script source and FIXTURES.md text | both `none` | ✓ PASS |
| Scope guard (no importer/DB code touched) | `git status --porcelain -- api pipeline alembic app data/corpus` | empty | ✓ PASS |

### Probe Execution

Not applicable — no `scripts/*/tests/probe-*.sh` convention exists in this project and no PLAN/SUMMARY declares one for this phase.

### Human Verification Required

None. The phase's one blocking human decision (`checkpoint:decision` in 41-03-PLAN.md Task 1) was already exercised during phase execution — the operator's verbatim answer ("confirm-as-proposed... no substitutions") is recorded in `.planning/FIXTURES.md`'s `## Confirmation` section and cross-checked above. All remaining must-haves are grep/script-verifiable and were independently re-run rather than trusted from SUMMARY claims.

### Gaps Summary

No gaps found. All 6 observable truths derived from ROADMAP Phase 41 success criteria are independently verified against live re-runs of `scripts/select_corpus_fixtures.py` and the committed `.planning/FIXTURES.md` — not merely accepted from SUMMARY.md narrative. The recommendation numbers, the tied runner-up, the state-variety fixtures, the CONFIRMED status, the apolitical containment, and the code/DB scope guard were all reproduced independently during this verification pass and matched the committed artifacts exactly.

---

_Verified: 2026-07-29T18:20:00Z_
_Verifier: Claude (gsd-verifier)_
