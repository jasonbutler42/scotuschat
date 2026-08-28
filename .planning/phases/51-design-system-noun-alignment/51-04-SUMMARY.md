---
phase: 51-design-system-noun-alignment
plan: 04
subsystem: api
tags: [fastapi, sqlalchemy, pydantic, pytest, term-grouping, apolitical-leak-ban]

requires:
  - phase: 51-design-system-noun-alignment
    provides: "plan 51-01's D-16 checkpoint resolution (Variant A — minimal term row) and plan 51-02's by-slug routes / derive_argument_slug reserved-word guard"
provides:
  - "GET /arguments/terms — term index with published-argument counts, api/services/arguments.py::list_terms"
  - "GET /arguments/term/{term_year} — term-scoped argument listing, api/services/arguments.py::list_arguments_for_term"
  - "api/schemas/arguments.py — TermSummary, TermIndexResponse, ArgumentListItem, TermArgumentsResponse"
  - "api/tests/test_public_arguments_listing.py — 16 behavioral + live-leak tests"
  - "Leak-ban and published-gate contracts extended to cover the new module/functions"
affects: [51-08-term-grouped-listing-frontend]

actuals:
  tokens: 8622
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Term-grouping query: GROUP BY Case.term_year reached through the CaseArgument.is_lead join, COUNT(DISTINCT Argument.id) so the join can never inflate a count, both published_at.isnot(None) and status==PUBLISHED predicates kept in addition to each other."
    - "Live leak-ban asymmetry proof: temporarily strip response_model + return a raw dict carrying a banned key on one route, confirm the live decoded-JSON assertion fails while the static declared-field sweep still passes (nothing to inspect with no declared model) — then revert byte-identical."

key-files:
  created:
    - api/schemas/arguments.py
    - api/tests/test_public_arguments_listing.py
  modified:
    - api/services/arguments.py
    - api/routers/arguments.py
    - api/tests/test_trust_public_leak_ban.py
    - api/tests/test_published_gate.py

key-decisions:
  - "D-16 Variant A (locked in plan 51-01) applied: no argument_participants -> people join, no advocates field. Verified via grep in both the acceptance criteria and this SUMMARY (0 occurrences of 'advocates:' and of the banned-derived-statistic field names in api/schemas/arguments.py)."
  - "Task 1's implementation edits (list_terms + list_arguments_for_term + both routes) were written together before the first commit, since both service functions share one base query shape and were more legible reviewed as a pair. Task 2's remaining scope was therefore test-only; this is a commit-granularity note, not a deviation — no code shipped ahead of its task's acceptance criteria being met."
  - "The plan's backstop truth (term-detail query cost measured at ~150-row term scale before the advocate join is committed to) was already satisfied by plan 51-01's checkpoint measurement, recorded in 51-DESIGN-DECISIONS.md's 'Term-row variant (D-16)' section — Variant A was selected, so this plan never builds the join the measurement was gating."

requirements-completed: [DS-01, DS-04]

coverage:
  - id: D1
    description: "GET /arguments/terms returns one row per October Term with at least one published argument, term_year + argument_count, ordered term_year descending, counting only published-gated arguments through the is_lead join with no double-count from consolidated dockets"
    requirement: "DS-04"
    verification:
      - kind: integration
        ref: "api/tests/test_public_arguments_listing.py#test_terms_empty_when_nothing_published"
        status: pass
      - kind: integration
        ref: "api/tests/test_public_arguments_listing.py#test_terms_counts_published_only_ordered_desc"
        status: pass
      - kind: integration
        ref: "api/tests/test_public_arguments_listing.py#test_terms_excludes_draft_argument"
        status: pass
      - kind: integration
        ref: "api/tests/test_public_arguments_listing.py#test_terms_excludes_unpublished_argument_with_retained_published_at"
        status: pass
      - kind: integration
        ref: "api/tests/test_public_arguments_listing.py#test_terms_consolidated_docket_contributes_one"
        status: pass
      - kind: integration
        ref: "api/tests/test_public_arguments_listing.py#test_terms_absent_when_only_argument_is_unpublished"
        status: pass
    human_judgment: false
  - id: D2
    description: "GET /arguments/term/{term_year} lists a term's published arguments (D-16 Variant A minimal shape: argument_id, slug, case_name, docket_number, term_year, argued_date, question_number), 200/empty for a real empty term, 422 for a bad year, stable ordering for a shared argued_date"
    requirement: "DS-04"
    verification:
      - kind: integration
        ref: "api/tests/test_public_arguments_listing.py#test_term_detail_lists_only_published_arguments_for_that_term"
        status: pass
      - kind: integration
        ref: "api/tests/test_public_arguments_listing.py#test_term_detail_real_empty_term_returns_200_not_404"
        status: pass
      - kind: integration
        ref: "api/tests/test_public_arguments_listing.py#test_term_detail_non_numeric_year_returns_422"
        status: pass
      - kind: integration
        ref: "api/tests/test_public_arguments_listing.py#test_term_detail_out_of_range_year_returns_422"
        status: pass
      - kind: integration
        ref: "api/tests/test_public_arguments_listing.py#test_term_detail_excludes_unpublished_with_retained_published_at"
        status: pass
      - kind: integration
        ref: "api/tests/test_public_arguments_listing.py#test_term_detail_consolidated_docket_contributes_one_row"
        status: pass
      - kind: integration
        ref: "api/tests/test_public_arguments_listing.py#test_term_detail_shared_argued_date_orders_stably"
        status: pass
      - kind: other
        ref: "grep -cE '^[[:space:]]*advocates[[:space:]]*:' api/schemas/arguments.py == 0"
        status: pass
      - kind: other
        ref: "grep -cE '^[[:space:]]*(utterance_count|speaking_time|duration|word_count|utterance_seconds|turn_count)[[:space:]]*:' api/schemas/arguments.py == 0"
        status: pass
    human_judgment: false
  - id: D3
    description: "Structural leak-ban extended to api/schemas/arguments.py (PUBLIC_SCHEMA_MODULE_PATHS), proven non-vacuous by a temporary trust_tier field that made it fail; published-gate contract extended to both new service functions; three live decoded-JSON leak assertions cover every new public payload (terms, term-detail, by-slug utterances) and are proven both to run (0 skipped) and to be non-vacuous (asymmetric experiment: live fails, static passes, with the model removed from response_model)"
    requirement: "DS-01"
    verification:
      - kind: integration
        ref: "api/tests/test_trust_public_leak_ban.py -q (129 passed)"
        status: pass
      - kind: integration
        ref: "api/tests/test_published_gate.py::TestTermGroupedListingPublishedGate (4 tests, all pass)"
        status: pass
      - kind: integration
        ref: "api/tests/test_public_arguments_listing.py#test_terms_live_response_never_leaks_trust_tier"
        status: pass
      - kind: integration
        ref: "api/tests/test_public_arguments_listing.py#test_term_detail_live_response_never_leaks_trust_tier"
        status: pass
      - kind: integration
        ref: "api/tests/test_public_arguments_listing.py#test_by_slug_utterances_live_response_never_leaks_trust_tier"
        status: pass
      - kind: other
        ref: "manual non-vacuity experiments (temporary trust_tier field; temporary response_model=None + raw dict), both reverted byte-identical, results recorded below"
        status: pass
    human_judgment: false

duration: 80min
completed: 2026-08-28
status: complete
---

# Phase 51 Plan 04: Term-Grouped Public Arguments API Summary

**Two new FastAPI endpoints (`GET /arguments/terms`, `GET /arguments/term/{term_year}`) replace `GET /cases`'s unbounded flat listing with a term-grouped index and drill-in view, backed by `list_terms`/`list_arguments_for_term` and D-16 Variant A's minimal row shape — the apolitical leak-ban and published-gate contracts extended and proven non-vacuous live rather than by inspection.**

## Performance

- **Duration:** ~80 min
- **Tasks:** 3
- **Files modified:** 6 (2 created, 4 modified)

## Accomplishments

- `api/schemas/arguments.py`: `TermSummary`/`TermIndexResponse` (term_year + argument_count) and `ArgumentListItem`/`TermArgumentsResponse` (D-16 Variant A's minimal row: argument_id, slug, case_name, docket_number, term_year, argued_date, question_number — no advocate join, no derived statistics).
- `api/services/arguments.py`: `list_terms` groups on `Case.term_year` through the same `CaseArgument.is_lead == True` join `get_cases()` uses, counts `DISTINCT Argument.id`, and keeps both `published_at.isnot(None)` and `status == PUBLISHED` predicates — never one instead of the other. `list_arguments_for_term` is the same base query scoped to one term, ordered by `argued_date DESC, id DESC` for stable tiebreaking.
- `GET /arguments/terms` and `GET /arguments/term/{term_year}` registered on `api/routers/arguments.py` — two-segment paths, no declaration-order dependency with the existing three/four-segment routes; `term_year` bounded `ge=1789, le=2200` so a bad year 422s before the service runs.
- `api/tests/test_public_arguments_listing.py` (16 tests): empty/counts/draft-exclusion/unpublished-exclusion/consolidated-docket/absence for the term index; published-only filtering/empty-term-200/bad-year-422/consolidated/stable-ordering for term detail; three live decoded-JSON leak assertions.
- `api/tests/test_trust_public_leak_ban.py`: `api/schemas/arguments.py` added to `PUBLIC_SCHEMA_MODULE_PATHS`. Collected test count unchanged (129 before and after this file's own edit — the new models were already reachable via the router-derivation Test 1 uses, since `api.routers.arguments` was already in `PUBLIC_ROUTER_MODULE_NAMES`), never shrunk.
- `api/tests/test_published_gate.py`: new `TestTermGroupedListingPublishedGate` (4 tests) asserts both predicates over both new service functions (30 -> 34 tests).
- Full suite: **1378 passed, 5 xfailed, 0 failed** (was 1318 pre-plan; +60 net new tests, zero regressions).

## Task Commits

1. **Task 1: Term index — `GET /arguments/terms`** — `674fe039d` (feat) — also carries Task 2's implementation (see Decisions Made)
2. **Task 2: Term detail — `GET /arguments/term/{term_year}`** — `c3783f036` (test) — test-only, implementation landed in commit 1
3. **Task 3: Extend the structural leak ban, add live leak assertions, extend the published-gate contract** — `883401dc9` (test)

**Plan metadata:** commit pending (this SUMMARY + STATE.md + ROADMAP.md progress update)

## Files Created/Modified

- `api/schemas/arguments.py` — new: `TermSummary`, `TermIndexResponse`, `ArgumentListItem`, `TermArgumentsResponse`
- `api/services/arguments.py` — new: `list_terms`, `list_arguments_for_term`
- `api/routers/arguments.py` — new routes: `GET /arguments/terms`, `GET /arguments/term/{term_year}`
- `api/tests/test_public_arguments_listing.py` — new: 16 behavioral + live-leak tests
- `api/tests/test_trust_public_leak_ban.py` — `PUBLIC_SCHEMA_MODULE_PATHS` extended, docstring note added
- `api/tests/test_published_gate.py` — `TestTermGroupedListingPublishedGate` added

## Decisions Made

- **D-16 Variant A applied as locked in plan 51-01.** No `argument_participants` -> `people` join, no `advocates` field on `ArgumentListItem`. The advocate join and its query-cost measurement remain deferred per `51-DESIGN-DECISIONS.md`'s "Term-row variant (D-16)" section, which already recorded the plan-shape-plus-projection cost analysis this plan's `must_haves.backstop` truth asked for — no new measurement was performed here since Variant A never builds the join.
- **Task 1's commit carries both new service functions and both new routes**, written together before the first commit since `list_terms`/`list_arguments_for_term` share one base query shape and reviewed more coherently as a pair. Task 2's remaining scope was therefore the term-detail behavioral tests only; no code shipped without its task's acceptance criteria (Task 1's own tests) passing first.
- **Both non-vacuity experiments in Task 3 were run live, not asserted:** (1) a temporary `trust_tier: str` field on `TermSummary` made `test_trust_public_leak_ban.py` fail (1 failed / 128 passed) before being reverted; (2) a temporary `response_model=None` route returning a raw dict with an injected `trust_tier` key made the live leak assertion FAIL while the static leak-ban module still PASSED (109 passed, fewer only because the model dropped out of the router-derivation set with the field removed — expected, not a regression), proving the live half catches what the static half structurally cannot. Both experiments were reverted; `git status`/`git diff` confirm the working tree is byte-identical to the pre-experiment committed state.

## Deviations from Plan

None — plan executed exactly as written. The Task 1/Task 2 commit-granularity note above is a documentation choice about *when* work was committed, not a change to *what* was built or a deviation from the plan's `<action>` instructions.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `GET /arguments/terms` and `GET /arguments/term/{term_year}` are ready for plan 51-08's frontend to consume (`app/src/routes/arguments/+page.server.ts` and the new `app/src/routes/arguments/term/[year]/+page.server.ts`), per the plan's `key_links`.
- `derive_argument_slug`'s reserved-word guard (D-13, plan 51-02) already guarantees `/arguments/term/{year}` can never be shadowed by an argument slug — no additional guard needed in 51-08.
- The old `GET /cases` endpoint remains live and untouched; its last consumer is removed in plan 51-08.

---
*Phase: 51-design-system-noun-alignment*
*Completed: 2026-08-28*

## Self-Check: PASSED

- All created files verified present on disk (`api/schemas/arguments.py`, `api/tests/test_public_arguments_listing.py`).
- All 3 commits verified in `git log`: `674fe039d`, `c3783f036`, `883401dc9`.
- All acceptance criteria for Tasks 1-3 re-run and confirmed passing.
- Full suite re-run after all changes: 1378 passed, 5 xfailed, 0 failed.
