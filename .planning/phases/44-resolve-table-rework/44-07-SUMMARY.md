---
phase: 44-resolve-table-rework
plan: 07
subsystem: ui
tags: [svelte, sveltekit, resolve-card, admin-pipeline, source-contract]

# Dependency graph
requires:
  - phase: 44-resolve-table-rework
    provides: "44-05's merged Resolved As cell (sideToggle + personDropdown stacked in one <td>, the personDropdown snippet, getRowCandidates) that this plan's sideScopedCandidates wraps"
provides:
  - "sideScopedCandidates — a client-side is_justice filter over the merged candidate list, fail-open on unknown side, inert while the side gate is open"
  - "Candidate.is_justice and ResolveCardProps.source type additions; the widened people local type in +page.server.ts"
  - "sourcePrefix — a single derived value replacing all four hardcoded 'Imported' prefixLabel literals with the job's real ingestion source ('Imported' for corpus, 'Extracted' for pdf)"
affects: [44-08, 44-09]

actuals:
  tokens: 4900
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Client-side convenience filter over an already-authorized dataset (Candidate.is_justice), explicitly not an access-control boundary — fails open on unknown data rather than hiding a real person"
    - "Snippet parameters kept explicit even when the value is also in script scope (descriptorCell takes sourcePrefix as its own parameter rather than closing over the outer derived value)"

key-files:
  created: []
  modified:
    - "app/src/lib/components/ResolveCard.svelte"
    - "app/src/routes/admin/pipeline/[job_id]/+page.server.ts"
    - "app/src/routes/admin/pipeline/[job_id]/+page.svelte"
    - "api/tests/test_phase44_resolve_table_contract.py"
    - "api/tests/test_phase38_extracted_value_contract.py"

key-decisions:
  - "A candidate with unknown is_justice (present only in a stale discrepancies snapshot) is shown on BOTH sides, not hidden from either — fail open per RESEARCH assumption A1."
  - "While a row's side gate is open, sideScopedCandidates returns the merged list unfiltered — there is no side to filter on yet."
  - "source is read from data.job (the load result), never liveJob (the 1s-polled copy) — a job's ingestion source is immutable for its life, so this keeps the hint prefix from ever flickering on a poll tick."
  - "descriptorCell's sourcePrefix is threaded in as an explicit snippet parameter, matching its existing params, rather than closed over implicitly."

patterns-established:
  - "A person the operator creates inline is enriched with is_justice from the side already known at creation time (handlePersonCreated), so it appears in its own side's filtered list without a refetch."

requirements-completed: [RESOLVE-09, RESOLVE-10]

coverage:
  - id: D1
    description: "Choosing Bench on a row narrows the person search to justices; choosing an advocate side narrows it to advocates; an unknown-side candidate stays reachable from both (fail-open)."
    requirement: "RESOLVE-09"
    verification:
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_side_scoped_candidates_filters_on_is_justice_not_labels"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_side_scoped_candidates_fails_open_on_unknown_side"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_side_scoped_candidates_skips_filtering_while_gated"
        status: pass
    human_judgment: true
    rationale: "Static source contracts prove the filter expression exists and branches correctly, but the operator-visible narrowing behavior in a live browser session was not exercised end-to-end (no frontend test runner exists in this repo, per 39-RESEARCH.md)."
  - id: D2
    description: "A person created inline through the popover appears immediately in the filtered list for the side they were created on."
    requirement: "RESOLVE-09"
    verification:
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_created_person_is_enriched_with_a_side"
        status: pass
    human_judgment: true
    rationale: "Static contract proves handlePersonCreated enriches the candidate with is_justice; the live browser round-trip (create -> appears without refetch) was not exercised."
  - id: D3
    description: "Every hint in the card takes its prefix from the job's real ingestion source ('Imported' for corpus jobs, 'Extracted' for PDF jobs); no hardcoded prefix remains."
    requirement: "RESOLVE-10"
    verification:
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_resolve_card_has_exactly_four_hint_usages"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_source_prefix_is_derived_from_the_source_prop"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_page_passes_source_from_load_data_not_the_polled_copy"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every CopyableExtractedValue call site elsewhere in the app still renders the app-wide default 'Extracted:' prefix; no backend, pipeline, or shared-component change was required."
    requirement: "RESOLVE-10"
    verification:
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_each_untouched_call_site_passes_no_prefix_label"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_copyable_extracted_value_default_prefix_unchanged"
        status: pass
    human_judgment: false

duration: 40min
completed: 2026-08-07
status: complete
---

# Phase 44 Plan 07: Side-scoped candidates and source-aware hint prefix Summary

**Person search now filters by `Person.is_justice` fail-open, and every ingestion hint's prefix is derived from the job's real `pdf`/`corpus` source instead of a hardcoded "Imported" literal — no backend, pipeline, or shared-component change required.**

## Performance

- **Duration:** ~40 min
- **Started:** 2026-08-07T13:30:00-05:00 (approx, read_first + research)
- **Completed:** 2026-08-07T14:08:40-05:00
- **Tasks:** 3 completed
- **Files modified:** 5 (2 components, 1 route load, 2 test files)

## Accomplishments

- Widened the load's `people` type and the `Candidate` interface to carry `is_justice`, closing the two overly-narrow TypeScript annotations that had been dropping the field between `GET /api/admin/people` and the dropdown.
- Added `sideScopedCandidates`, a named function wrapping `getRowCandidates` that filters the merged list on `is_justice` — fails open (keeps, never hides) a candidate whose side is unknown, and is a no-op while the row's side gate is still open.
- Enriched `handlePersonCreated`'s candidate with `is_justice` derived from the side already known at creation time, and side-scoped the create-person trigger label ("Create new bench person" / "Create new advocate").
- Threaded `Job.source` from the load data through to `ResolveCard`'s new `source` prop and derived a single `sourcePrefix` value ('Imported' for corpus, 'Extracted' for pdf), replacing all four hardcoded `prefixLabel="Imported"` literals — including through `descriptorCell` as an explicit snippet parameter.
- Extended the shared Phase 44 contract file with a `Plan 44-07` banner (14 new tests) covering both requirements, and re-pointed the 44-04 section's four-hint-prefix assertion at the new derived expression.

## Task Commits

Each task was committed atomically:

1. **Task 1: Side-scope the candidate list by is_justice** - `ef6f4975` (feat)
2. **Task 2: Derive the hint prefix from the job's ingestion source** - `5f664ce9` (feat)
3. **Task 3: Contract tests for side-scoped candidates and the source-aware prefix** - `418d60d8` (test)

## Files Created/Modified

- `app/src/lib/components/ResolveCard.svelte` - `Candidate.is_justice`, `sideScopedCandidates`, `handlePersonCreated` enrichment, side-scoped create-person trigger label, `ResolveCardProps.source`, `sourcePrefix` derived value, all four `CopyableExtractedValue` call sites re-pointed
- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` - widened the `people` local's type to `{ id, full_name, is_justice }`, dropping the never-real `role_name` field
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` - `Job.source`, the `<ResolveCard source={data.job.source ?? 'pdf'} />` prop
- `api/tests/test_phase44_resolve_table_contract.py` - new Plan 44-07 banner (14 tests) plus the re-pointed 44-04 prefix assertion
- `api/tests/test_phase38_extracted_value_contract.py` - re-pointed one Phase 38 test's prefix assertion (see Deviations)

## Decisions Made

- `is_justice` is the sole filter field — never `role_name` or `SIDE_LABEL` — matching the People directory's own Bench/Advocate tab semantics (RESEARCH Anti-Patterns).
- `source` is read from `data.job`, not `liveJob`: a job's ingestion source is immutable for its life, so reading it from the load data means the hint prefix cannot flicker on a poll tick.
- `descriptorCell`'s prefix is passed as an explicit snippet parameter (named `sourcePrefix`, shadowing the outer derived value within the snippet's own scope) rather than reached for implicitly, matching the snippet's existing explicit-parameter style.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `test_phase38_extracted_value_contract.py` regressed when the hardcoded "Imported" literal was retired**

- **Found during:** Task 3, running the full `api/tests` suite per the plan's own verification step.
- **Issue:** `test_resolve_card_hints_opted_out_of_stacked_confidence_raw_per_phase_44` (in `test_phase38_extracted_value_contract.py`, a file outside this plan's declared `files_modified`) asserted `source.count('prefixLabel="Imported"') == 4`. Task 2's intentional, plan-mandated replacement of that literal with `prefixLabel={sourcePrefix}` made this a genuine regression, not a false positive — the assertion was checking for exactly the string the plan required to disappear.
- **Fix:** Re-pointed the assertion at `source.count("prefixLabel={sourcePrefix}") == 4`, matching the same derived expression `test_phase44_resolve_table_contract.py`'s Plan 44-07 section now asserts. The test's other assertions (no `confidence=`, no mirrored `raw` prop, no leftover caller-owned prefix text) are unchanged.
- **Files modified:** `api/tests/test_phase38_extracted_value_contract.py`
- **Verification:** `./.venv/Scripts/python.exe -m pytest tests/conftest.py api/tests -q` — 619 passed, 4 pre-existing collection errors (unrelated, documented below), 0 failures.
- **Committed in:** `418d60d8` (part of Task 3's commit)

---

**Total deviations:** 1 auto-fixed (Rule 1).
**Impact on plan:** The plan's own file `git diff --name-only` acceptance check for Task 3 (expecting only `test_phase44_resolve_table_contract.py`) does not account for this cross-file regression; the fix was necessary to satisfy the plan's own higher-priority requirement that the full `api/tests` suite report 0 failures. No scope creep — the second file's change is a one-line re-point of an assertion made stale by this plan's intentional change, not new functionality.

## Issues Encountered

None beyond the deviation above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Both RESOLVE-09 and RESOLVE-10 are complete: the person search is side-scoped with a documented fail-open rule, and every hint prefix reflects the job's real ingestion source.
- No backend endpoint, query parameter, column, migration, or shared-component change was needed — confirmed by empty diffstats on `api/`, `pipeline/`, `CopyableExtractedValue.svelte`, and `CreatePersonPopover.svelte`.
- 44-08 and 44-09 (remaining Figma reconciliation plans) can proceed; this plan's Deltas section flagged the bench-side create-person trigger copy ("Create new bench person") for 44-09's final visual acceptance to confirm.

---
*Phase: 44-resolve-table-rework*
*Completed: 2026-08-07*
