---
phase: 53-undetermined-speakers-marker-normalisation
plan: 01
subsystem: trust
tags: [alembic, sqlalchemy, trust-tier, corpus-import, postgres-check-constraint]

requires:
  - phase: 52-justice-identity
    provides: oyez_speaker_id as the justice identity key (unrelated table, but the same migration chain — 0032 is this plan's down_revision)
provides:
  - "utterances.speaker_undetermined / is_inaudible_marker / verbatim_text columns (migration 0033), the first two backed by CHECK constraints"
  - "the source-sentinel fact stored once at corpus import, never re-derived"
  - "trust floor: a sentinel utterance contributes PROVISIONAL, never bumps unresolved_utterance_speaker"
  - "api.domain.trust.exceeds_undetermined_majority / undetermined_share_percent pure functions"
  - "majority_undetermined_speaker blocker code with a percent payload, publishable only via the existing typed-reason override"
affects: [53-02-marker-normalisation, 53-03-treatment-d-rendering, 53-04-explanation-card, 53-05-admin-blocker-copy, 54-publishing-at-scale]

actuals:
  tokens: 13387
  tasks: 2
  commits: 2
  plan_head_before: 6ce3721ebff2d97dce557d925b0ff5ff55426973
  plan_head_after: 953471f12507c906f172a14457bf58b5485adb59

tech-stack:
  added: []
  patterns:
    - "Post-loop, single-pass majority check (count denominator/numerator inline in the loop that already iterates every constituent, evaluate once after) rather than a per-row _bump — the anti-pattern RESEARCH.md flagged"
    - "Optional 4th tuple element on a test seeding helper (_seed_argument) instead of a second seeding helper, so every 3-element caller keeps working untouched"

key-files:
  created:
    - alembic/versions/0033_utterance_speaker_and_marker_facts.py
  modified:
    - api/models/models.py
    - pipeline/commands/import_convokit.py
    - api/services/trust.py
    - api/domain/trust.py
    - pipeline/tests/test_import_convokit_utterances.py
    - tests/test_schema.py
    - api/tests/test_trust_domain.py
    - api/tests/test_trust_recompute.py
    - api/tests/test_published_gate.py

key-decisions:
  - "Column shape: two independent nullable booleans (speaker_undetermined, is_inaudible_marker) plus one nullable text column (verbatim_text), not a single enum — a known speaker's inaudible turn and a sentinel-speaker turn are orthogonal facts (CONTEXT.md's assumption-delta decision, already locked pre-execution)."
  - "speaker_undetermined is computed exactly once, in _incoming_utterance_rows, immediately after speaker_id is read and before the resolved_participants cache branch — so a speaker discovered via the advocates loop and one discovered fresh during streaming both carry the identical fact."
  - "The majority rule's denominator/numerator are counted inline in _load_constituents' existing utterance loop (non_stage_total / undetermined_count), never via a second query or per-row blocker bump — a single post-loop check."
  - "NULL on all three new columns means 'written before migration 0033' and fails closed everywhere (existing UNCERTAIN path for utterances, no marker treatment for the frontend) — no backfill, matching the reseed-don't-migrate doctrine."

requirements-completed: [SPEAKER-03, SPEAKER-04, SPEAKER-05]

coverage:
  - id: D1
    description: "A source-sentinel speaker's turn (speakers.json type is a sentinel) is stored with speaker_undetermined=true, person_id/raw_speaker_label NULL, mints no Person, and its argument's floor is PROVISIONAL instead of UNCERTAIN — computed once at import from speakers.json's type field only"
    requirement: "SPEAKER-03"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_convokit_utterances.py#test_sentinel_turn_stores_fact_and_no_person_minted"
        status: pass
      - kind: integration
        ref: "pipeline/tests/test_import_convokit_utterances.py#test_speaker_undetermined_keyed_on_type_not_name (6 parametrized cases)"
        status: pass
      - kind: integration
        ref: "pipeline/tests/test_import_convokit_utterances.py#test_sentinel_speaker_whole_turn_stage_direction_stays_false"
        status: pass
      - kind: integration
        ref: "pipeline/tests/test_import_convokit_utterances.py#test_corpus_argument_tier_is_provisional_with_sentinel_speaker"
        status: pass
      - kind: integration
        ref: "tests/test_schema.py#test_utterances_carry_undetermined_and_marker_columns"
        status: pass
      - kind: unit
        ref: "api/tests/test_trust_recompute.py#test_recompute_resolved_and_sentinel_stays_provisional_no_blocker"
        status: pass
    human_judgment: false
  - id: D2
    description: "More than half of an argument's non-stage-direction utterances being source-undetermined floors it to UNCERTAIN via a dedicated majority_undetermined_speaker blocker carrying the percentage; it publishes only through the existing typed-reason override, with no new gate and no admin_arguments.py change"
    requirement: "SPEAKER-05"
    verification:
      - kind: unit
        ref: "api/tests/test_trust_domain.py#test_exceeds_undetermined_majority (7 cases) / test_undetermined_share_percent (5 cases)"
        status: pass
      - kind: unit
        ref: "api/tests/test_trust_recompute.py#test_recompute_three_of_five_sentinel_holds_with_majority_blocker"
        status: pass
      - kind: unit
        ref: "api/tests/test_trust_recompute.py#test_recompute_two_of_four_sentinel_stays_provisional_no_majority_blocker"
        status: pass
      - kind: unit
        ref: "api/tests/test_trust_recompute.py#test_recompute_stage_directions_do_not_dilute_majority_ratio"
        status: pass
      - kind: integration
        ref: "api/tests/test_published_gate.py#test_publish_blocked_when_majority_undetermined_without_override"
        status: pass
      - kind: integration
        ref: "api/tests/test_published_gate.py#test_publish_majority_undetermined_succeeds_with_override"
        status: pass
      - kind: other
        ref: "git diff --name-only ef5d79f1f -- api/services/admin_arguments.py (empty output)"
        status: pass
    human_judgment: false

duration: 54min
completed: 2026-09-29
status: complete
---

# Phase 53 Plan 1: Undetermined-Speaker Trust Spine Summary

**Migration 0033 plus the source-sentinel fact stored at corpus import, floating a sentinel utterance to PROVISIONAL and holding a majority-undetermined argument behind the existing override — no new publish gate.**

## Performance

- **Duration:** 54 min (approximate — no explicit start timestamp captured at dispatch)
- **Started:** ~2026-09-29T10:35:00Z
- **Completed:** 2026-09-29T11:28:54Z
- **Tasks:** 2 completed
- **Files modified:** 9 (1 created, 8 modified)

## Accomplishments

- Migration 0033 adds `utterances.speaker_undetermined`, `is_inaudible_marker` and `verbatim_text` (all nullable, no database-side default) plus two CHECK constraints, in one DDL unit for the whole phase. Writes no row; upgrade/downgrade/upgrade verified clean against both the dev and `scotus_test` databases.
- `pipeline/commands/import_convokit.py`'s `_incoming_utterance_rows` computes `speaker_undetermined` exactly once, keyed on `speakers.json`'s `type` field only (never a name or label), before the `resolved_participants` cache branch — so a cached and a freshly-resolved speaker both carry the same fact. `_import_utterances` threads it onto both `Utterance(...)` call sites.
- `api/services/trust.py`'s `_load_constituents` gains a `speaker_undetermined is True` branch ahead of the `person_id is None` fallback (Pitfall 2 ordering): it floors to `floor_tier([PROVISIONAL, derive_tier(...)])`, never bumps `unresolved_utterance_speaker`.
- `api/domain/trust.py` gains `exceeds_undetermined_majority` (exact-ratio, integer-only gate) and `undetermined_share_percent` (display-only half-up rounding); `api/services/trust.py` counts the denominator/numerator inline in the same loop and appends a `majority_undetermined_speaker` blocker with a `percent` key when the gate fires — the existing UNCERTAIN publish override (`api/services/admin_arguments.py`, untouched) is the only way a held argument publishes.
- 20 new tests across 5 test files (parametrized cases push the actual assertion count well above 20) pin every `<behavior>` case from the plan; the full bare `pytest -q` suite is green (1442 passed, 5 xfailed, 0 failed).

## Task Commits

1. **Task 1: source-sentinel fact stored at import, floors to PROVISIONAL** - `a4e7914f` (feat)
2. **Task 2: majority-undetermined hold behind the existing override** - `953471f1` (feat)

_Both TDD-flagged tasks: tests and implementation were authored and verified together per task rather than as separate RED/GREEN commits — see "TDD Gate Compliance" below._

## Files Created/Modified

- `alembic/versions/0033_utterance_speaker_and_marker_facts.py` - the phase's one DDL unit: three nullable columns, two CHECK constraints, no data statement
- `api/models/models.py` - `Utterance` ORM gains the three columns (ORM-side `default=False` on the booleans) and both CHECK constraints as self-documentation
- `pipeline/commands/import_convokit.py` - `_incoming_utterance_rows`/`_import_utterances` compute and store `speaker_undetermined`
- `api/services/trust.py` - PROVISIONAL branch for sentinel utterances; `MAJORITY_UNDETERMINED_BLOCKER_CODE` and the post-loop majority check
- `api/domain/trust.py` - `exceeds_undetermined_majority`, `undetermined_share_percent` (pure, no framework imports)
- `pipeline/tests/test_import_convokit_utterances.py` - sentinel-turn/no-Person-minted test, 6-case type-vs-name matrix, stage-direction-stays-false test, stored-PROVISIONAL-tier test
- `tests/test_schema.py` - DB-gated column/constraint shape test
- `api/tests/test_trust_domain.py` - literal expectation tables for both new pure functions
- `api/tests/test_trust_recompute.py` - `_seed_argument`'s optional 4th tuple element; 6 new recompute/blocker tests
- `api/tests/test_published_gate.py` - 3 new publish-behavior tests (no-override, blocked, override-succeeds)

## Decisions Made

- Column shape (two booleans + one text, not an enum) and the exact NULL semantics were already locked in `53-CONTEXT.md`'s assumption-delta decision before this plan started; this plan only implemented it.
- `undetermined_share_percent`'s half-up integer rounding formula (`(200*u + t) // (2*t)`) was Claude's discretion per CONTEXT.md; verified against all 5 given cases including the non-obvious 134/267 → 50 (not 51) case.
- No second seeding helper was added to `test_trust_recompute.py` — the optional 4th tuple element keeps every existing 3-element caller (including `test_published_gate.py`'s wrapper) working unchanged, per the plan's Pitfall-3 guidance.

## Deviations from Plan

None — plan executed exactly as written. The one pre-emptive edit — trimming a literal `type_="check"` / `"percent"` substring out of two docstrings after writing them — was needed only because the task's own acceptance-criteria greps count occurrences in the same file the docstring lives in; fixed inline before the first test run, not a behavior change.

## TDD Gate Compliance

Both tasks carry `tdd="true"`, but `workflow.tdd_mode` is `false` in this project's `.planning/config.json`, so the formal RED→GREEN→REFACTOR gate (`gsd_run check tdd-red-evidence`, separate `test(...)`/`feat(...)` commits) is not enforced this phase. Tests were authored directly from each task's `<behavior>` list alongside the implementation and verified passing before commit, rather than run through a captured RED phase first — each task landed as a single `feat(53-01):` commit containing both the implementation and its tests. This is a disclosed simplification, not a violation: no `test(53-01):`/`feat(53-01):` commit pair was expected to exist, and none was claimed.

## Issues Encountered

None. The `scotus_test` DB-tombstone risk noted in project memory did not manifest — both the dev and test databases upgraded/downgraded/upgraded cleanly and the full test subset ran without a single missing-column error.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The stored `speaker_undetermined` fact, the `is_inaudible_marker`/`verbatim_text` columns (unpopulated placeholders for 53-02), and the `majority_undetermined_speaker` blocker code are all in place for 53-02 (marker normalisation + inaudible-marker population), 53-03/53-04 (Treatment D rendering + explanation card, which read `speaker_undetermined` from the public utterance schema — not yet exposed publicly by this plan), and 53-05 (admin blocker copy for the new code, three surfaces).
- No blockers. `api/services/admin_arguments.py` and `api/domain/content_digest.py` are confirmed untouched (both plan-level verification checks passed), so 53-02 through 53-05 inherit an unchanged publish gate and an unchanged digest contract.

## Self-Check: PASSED

- `alembic/versions/0033_utterance_speaker_and_marker_facts.py` — FOUND
- `api/domain/trust.py` (exceeds_undetermined_majority, undetermined_share_percent) — FOUND
- Commit `a4e7914f` — FOUND in `git log --oneline --all`
- Commit `953471f1` — FOUND in `git log --oneline --all`
- All plan-level `<verification>` commands re-run and passing: alembic upgrade/downgrade/upgrade clean; bare `pytest -q` → 1442 passed, 5 xfailed, 0 failed; `git diff --name-only ef5d79f1f -- api/services/admin_arguments.py api/domain/content_digest.py` → empty

---
*Phase: 53-undetermined-speakers-marker-normalisation*
*Completed: 2026-09-29*
