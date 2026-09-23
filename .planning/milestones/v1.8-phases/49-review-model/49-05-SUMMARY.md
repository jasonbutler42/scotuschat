---
phase: 49-review-model
plan: 05
subsystem: review-model
tags: [sveltekit, svelte5, fastapi, sqlalchemy, admin-ui, trust-tier, review-state]

requires:
  - phase: 49-review-model plan 01
    provides: "the /admin/review tracer (queue table skeleton, Confirm action, admin_job_id deep-link routing) this plan extends rather than replaces"
  - phase: 49-review-model plan 04
    provides: "the full resolve-action set (confirm/confirm_unattributable/reflag), the People-tab list/PATCH routes, and discrepancy attachment this plan's UI drives"

provides:
  - "api/services/admin_review.py: list_review_queue_arguments/list_review_queue_people gain status/tier/review_state filters (D-07 allow-list idiom) and the full D-03 sort (published-but-degraded first, tier rank, argued_date ASC NULLS LAST, Argument.id ASC tie-break, then the existing side/id constituent tie-break); each argument item carries a real summarize_tier_blockers breakdown"
  - "get_review_queue_stats + GET /api/admin/review/stats — dedicated COUNT queries sharing the exact inclusion predicates the list queries use (_argument_attention_predicate/_person_attention_predicate), so the dashboard card and the screen can never disagree"
  - "The full /admin/review screen: Arguments|People tabs, the three-axis filter row, the active-filter indicator, expandable argument rows (full-width <tr> beneath the trigger row, never a native disclosure element) with per-constituent identity/side-hint/review_state badge/discrepancy detail/fixed-order actions, and the zero-constituent blockers fallback panel"
  - "AdminSubNav gains a Review link; the admin dashboard gains a fifth StatCard on a widened 5-column grid, with the zero-state non-link and pluralized-link variants"
  - "api/tests/test_phase49_review_ui_contract.py — 14-test source contract, including 2 of the plan's 4 backstop statements; 2 more backstop tests added to test_admin_review_service.py"

affects: [49-06]

actuals:
  tokens: 26183
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Shared inclusion-predicate builder functions (_argument_attention_predicate/_person_attention_predicate) factored out of the list queries so a dedicated COUNT query can reuse the identical WHERE expression — the dashboard card and the screen's own list can never disagree by construction, not by convention"
    - "Full-page goto()-driven filter composition via URLSearchParams (no client-side filter state) — every filter/tab is a query-param round trip, matching every other admin list page's established idiom"

key-files:
  created:
    - api/tests/test_phase49_review_ui_contract.py
  modified:
    - api/services/admin_review.py
    - api/schemas/admin_review.py
    - api/routers/admin_review.py
    - api/tests/test_admin_review_service.py
    - app/src/routes/admin/review/+page.server.ts
    - app/src/routes/admin/review/+page.svelte
    - app/src/lib/components/AdminSubNav.svelte
    - app/src/routes/admin/+page.server.ts
    - app/src/routes/admin/+page.svelte

key-decisions:
  - "Person's provenance-note format deviates from the plan's literal \"{Source} · {method}\" spec: Person.provenance_metadata has no `method` field anywhere in its writers (pipeline/commands/import_convokit.py, import_justices_csv.py, alembic/versions/0022_person_name_authority.py all write {source, raw, confidence, reason, auto_applied}). Implemented as \"{Source} · {confidence}\" instead — confidence (High/Medium/Low) is the closest short, structured analog; reason is a full sentence unsuitable for a compact note. Source wins over spec prose, matching this plan's own <planner_decisions> precedent (StatCard grid, Edit deep-link target)."
  - "Confirm's render condition on the Arguments tab stayed person_id !== null && review_state === 'needs_review' — the exact rule the inherited context marked 'still in force' from the Wave 1 tracer feedback gate — rather than rendering unconditionally. This makes the UI-SPEC's E7 unresolved-decision scenario ('an unresolved-speaker constituent that has already been confirmed genuinely co-renders all four actions') unreachable in practice: Confirm requires needs_review, Re-flag requires operator_confirmed/operator_edited, and those states are mutually exclusive on one row, so at most 3 of the 4 actions can co-render on any single constituent. flex-wrap: wrap is applied regardless so the achievable 2-3-action case never overflows. See Deviations."
  - "get_review_queue_arguments'/get_review_queue_people's review_state filter narrows WITHIN the D-05 attention-worthy inclusion set rather than widening it — an operator filtering to review_state=operator_confirmed on the Arguments tab will see zero rows unless an otherwise-flagged argument also happens to have a confirmed constituent, since operator_confirmed alone never satisfies inclusion. This matches D-07's own framing (filters narrow, they do not widen) and is exercised by the review_state filter tests."

patterns-established:
  - "A dashboard StatCard's backing count and a list screen's own filtered view must read from the same predicate-builder function, not two independently-written WHERE clauses — the D-30 lesson this plan encodes as _argument_attention_predicate/_person_attention_predicate."

requirements-completed: []

coverage:
  - id: D1
    description: "list_review_queue_arguments/list_review_queue_people gain status × tier × review_state filters with an unrecognised-value-applies-no-filter allow-list convention, and the full D-03 deterministic sort (published-degraded first, tier rank, argued_date ASC NULLS LAST, Argument.id ASC tie-break — never created_at, which does not exist on Argument)"
    requirement: "REVIEW-03"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_review_service.py#test_argument_satisfying_all_three_inclusion_legs_appears_exactly_once"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_review_service.py#test_published_uncertain_argument_sorts_above_non_published_regardless_of_date"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_review_service.py#test_same_tier_same_date_arguments_return_in_stable_id_order_across_calls"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_review_service.py#test_null_argued_date_sorts_after_dated_arguments_in_same_tier"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_review_service.py#test_tier_filter_narrows_and_unrecognized_value_applies_no_filter"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_review_service.py#test_review_state_filter_narrows_arguments_to_matching_constituent"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_review_service.py#test_status_filter_accepts_candidate_independent_of_arguments_list_allowlist"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_review_service.py#test_people_query_orders_needs_review_then_unreviewed_then_name"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_review_service.py#test_review_state_filter_narrows_people_to_matching_state"
        status: pass
      - kind: other
        ref: "curl localhost:8000/api/admin/review/arguments?tier=uncertain&status=candidate — 200, only matching rows; ?tier=banana — unfiltered"
        status: pass
    human_judgment: false
  - id: D2
    description: "get_review_queue_stats + GET /api/admin/review/stats: dedicated COUNT queries sharing the exact inclusion predicates the list queries use, never materializing the unbounded list"
    requirement: "REVIEW-03"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_review_service.py#test_get_review_queue_stats_counts_via_dedicated_count_queries"
        status: pass
      - kind: other
        ref: "grep -c 'func.count' api/services/admin_review.py -> 2; curl localhost:8000/api/admin/review/stats -> {arguments,people,total} all integers"
        status: pass
    human_judgment: false
  - id: D3
    description: "Each argument item carries a real summarize_tier_blockers breakdown, so a zero-flagged-constituent degraded row has something real to show in the expanded panel (49-05 <planner_decisions> E5 empty)"
    requirement: "REVIEW-03"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_review_service.py#test_zero_constituent_degraded_argument_carries_real_blockers"
        status: pass
    human_judgment: false
  - id: D4
    description: "The full /admin/review screen: Arguments|People tabs, three-axis filter row + active-filter indicator, expand/collapse via a full-width <tr> (never a native disclosure element), per-constituent identity/side-hint/badges/discrepancy detail, and the fixed-order action row"
    requirement: "REVIEW-03"
    verification:
      - kind: other
        ref: "api/tests/test_phase49_review_ui_contract.py (14 tests) — tabs, status segments, filter option labels, all 5 badge hexes exactly once, aria-expanded present with no native disclosure element, flex-wrap on filter/action rows, no text-overflow/class=, 4 action labels verbatim, both empty-state bodies, subnav link, dashboard grid/StatCard count"
        status: pass
      - kind: other
        ref: "npm --prefix app run check -> 0 errors, 37 warnings (same baseline as 49-03)"
        status: pass
    human_judgment: true
    rationale: "This screen's interactive/visual behavior (filter composition surviving a back-button press, expand/collapse toggling live, Confirm/Confirm-as-unattributable/Re-flag acting on the right row and the row staying visible with its new badge, the five StatCards sitting evenly in one row, no horizontal scroll at 375px) requires an authenticated browser session against /admin/**. This sandbox's permission policy denies reading .env (where ADMIN_USERNAME/ADMIN_PASSWORD/SESSION_SECRET live), and per this org's credential-handling posture this executor did not attempt to work around that denial — consistent with 49-01's and 49-03's own recorded gap. A human must complete the Task 2 <human-check> seven-item browser walkthrough before this plan is UAT-complete. A green source-contract test is not behavioral evidence (the $state proxy trap already let 28 green tests pass against a fully broken button in Phase 48 plan 48-10)."
  - id: D5
    description: "The dashboard entry point (AdminSubNav Review link; the 5-column grid + fifth StatCard with zero-state non-link and pluralized-link variants) and the Resolve/Reflag/Confirm-as-unattributable form actions wired to the backend's PATCH routes"
    requirement: "REVIEW-04"
    verification:
      - kind: other
        ref: "grep -c '/admin/review' AdminSubNav.svelte -> 1; grep -c 'grid-template-columns: repeat(5, 1fr)' admin/+page.svelte -> 1; grep -c '<StatCard' -> 5; curl localhost:8000/api/admin/review/stats confirms the backing counts the card renders"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_review_service.py (28 tests total, including plan 49-04's confirm/confirm_unattributable/reflag behavior tests re-verified green against this plan's extended queries)"
        status: pass
    human_judgment: true
    rationale: "The three form actions' end-to-end wiring from a click in the browser through the SvelteKit action to the FastAPI PATCH and back to a redirected, re-rendered row with its new badge (D-26) has not been exercised live for the same credential-access reason as D4. The backend actions themselves were exhaustively tested in plan 49-04; what remains unverified here is the new frontend form markup's actual submit behavior."

duration: 50min
completed: 2026-08-23
status: complete
---

# Phase 49 Plan 05: Review UI Summary

**The full `/admin/review` operator queue screen — Arguments/People tabs, the trust-tier × review-state × status filter set with a fully specified server-side sort, expandable argument rows with discrepancy detail and the four-action fixed-order row, plus the AdminSubNav entry and a fifth dashboard StatCard backed by a dedicated COUNT query that shares its inclusion predicate with the list itself.**

## Performance

- **Duration:** ~50 min
- **Tasks:** 3
- **Files touched:** 10 (1 created, 9 modified)
- **Commits:** 3

## Accomplishments

- **Backend queries (Task 1)** — `list_review_queue_arguments`/`list_review_queue_people` gained `status`/`tier`/`review_state` filters via the `admin_people.py::missing_filters` allow-list idiom (an unrecognised value applies no filter) and the full D-03 sort: published-but-degraded floats to the top regardless of date, then tier rank, then `argued_date` ASC NULLS LAST, then `Argument.id` ASC as the deterministic tie-break (never `created_at`, which does not exist on `Argument` and is documented as unreliable on reset fixtures — the exact defect that produced Phase 48's ordering bug). The existing `ArgumentParticipant.side`/`.id` constituent tie-break from plan 49-01's tracer feedback gate fix is unchanged. Each argument item now carries a real `summarize_tier_blockers` breakdown so a zero-flagged-constituent degraded row has something to show in the expanded panel.
- **Dashboard COUNT (Task 1)** — `get_review_queue_stats` + `GET /api/admin/review/stats` return `{arguments, people, total}` from two dedicated `COUNT` queries built on the SAME `_argument_attention_predicate`/`_person_attention_predicate` functions the list queries use — factored out specifically so the dashboard card and the screen's own filtered list can never disagree.
- **The full queue screen (Task 2)** — Arguments|People tabs (full-page `goto()` round trip, filters reset on tab switch); the three-axis filter row (5-segment status control, trust-tier `<select>` Arguments-only, review-state `<select>` both tabs); the active-filter indicator naming up to three active filters; expand/collapse via a full-width `<tr>` beneath the trigger row (the exact publish-blocked-panel technique from `admin/arguments/+page.svelte`, never a native disclosure element); per-constituent blocks with identity ("Unresolved speaker" for `person_id IS NULL`), the Bench/Advocate side hint (`ResolveCard.svelte`'s own formula), the `review_state` badge, the Discrepancy badge + detail lines (absent side rendered as the literal `(none)`), and the fixed-order Confirm → Confirm-as-unattributable → Edit → Re-flag action row; a zero-constituent argument's expanded panel falls back to the `blockerSentence` breakdown instead of rendering empty.
- **Entry points (Task 2)** — `AdminSubNav` gained a "Review" link between Arguments and People Editor; the admin dashboard's stat-card grid widened from a literal 4-column to a 5-column `grid-template-columns` (verified source contradicted the UI-SPEC's "absorbs without change" claim) and gained a fifth "Review queue" `StatCard` with the zero-state non-link ("No items need review") and pluralized-link (`"1 item needs review →"` / `"{N} items need review →"`) variants.
- **Source contract + backstops (Task 3)** — new `api/tests/test_phase49_review_ui_contract.py` (14 tests) locks the screen's structural contract; two of the plan's four held-out UI-SPEC backstop statements (E1 zero-one-many's strict `=== 1` plural keying, E5 zero-one-many's shared one-`{#each}`-loop/16px-gap layout) are pinned there, spot-checked by deleting the singular branch and confirming the test fails before reverting. The other two (E6 partial's one-sided-discrepancy `(none)` rendering, E6 long-text's untruncated 300-char round-trip with no `text-overflow`/`nowrap`/`width:` on the discrepancy line) are pinned as data-shape tests in `test_admin_review_service.py`.
- **Full suite: 1403 passed, 5 xfailed, 0 failed** — exactly +27 over the 1376-test baseline (11 new argument/people query tests + 2 new backstop service tests + 14 new contract-module tests).

## Task Commits

1. **Task 1 — filterable, deterministically sorted queue queries + dashboard COUNT:** `cc0e5ee24` (feat)
2. **Task 2 — full queue screen, subnav entry, dashboard StatCard:** `562f26c19` (feat)
3. **Task 3 — source contract + 4 held-out backstop tests:** `e731fb38e` (test)

## Files Created/Modified

- `api/services/admin_review.py` — `_argument_attention_predicate`/`_person_attention_predicate`/`_person_provenance_note` helpers; filters + full sort on both list queries; `blockers` attached per argument; new `get_review_queue_stats`
- `api/schemas/admin_review.py` — `ReviewQueueArgumentItem.blockers`; `ReviewQueueStats` reshaped to `{arguments, people, total}`
- `api/routers/admin_review.py` — query params on `GET /arguments`/`GET /people`; new `GET /stats`
- `api/tests/test_admin_review_service.py` — 13 new tests (11 Task 1 behavior-bullet tests + 2 Task 3 backstop tests); 28 total
- `api/tests/test_phase49_review_ui_contract.py` — new, 14 tests
- `app/src/routes/admin/review/+page.server.ts` — tab/status/tier/review_state read from the URL and forwarded per-tab; `confirm`/`confirmUnattributable`/`reflag` form actions
- `app/src/routes/admin/review/+page.svelte` — the full Screen Contract (583 new lines)
- `app/src/lib/components/AdminSubNav.svelte` — new "Review" link
- `app/src/routes/admin/+page.server.ts` — sixth degrade-gracefully fetch against `/api/admin/review/stats`
- `app/src/routes/admin/+page.svelte` — 5-column grid; fifth `StatCard`

## Decisions Made

See `key-decisions` in frontmatter above.

## Deviations from Plan

### Auto-fixed / Directed Issues

**1. [Rule 1 - Bug, plan text contradicted by verified source] Person provenance-note format uses `confidence`, not `method`**
- **Found during:** Task 1, while implementing `list_review_queue_people`'s provenance-note field
- **Issue:** The plan's action text specifies `"{Source} · {method}"`, but `Person.provenance_metadata` has no `method` field anywhere in the three code paths that write it (`pipeline/commands/import_convokit.py:721`, `pipeline/commands/import_justices_csv.py:307`, `alembic/versions/0022_person_name_authority.py`'s legacy backfill) — all write exactly `{source, raw, confidence, reason, auto_applied}`. `method` exists only on `ArgumentParticipant` (which has real `source`/`method` columns); Person's D-08 fold deliberately left person-level authority entirely on `review_state` instead.
- **Fix:** Implemented `"{Source} · {confidence}"` (title-cased source, em dash when both absent) — `confidence` (High/Medium/Low) is the closest short, structured analog to a compact second field; `reason` is a full sentence and was rejected as too long for this column.
- **Files modified:** `api/services/admin_review.py` (`_person_provenance_note`)
- **Verification:** `test_people_query_orders_needs_review_then_unreviewed_then_name` and the People-tab review_state filter test exercise the same query path; the provenance-note field itself has no dedicated assertion beyond the schema round-trip (documented gap, not a defect — no test asserts the exact note string).
- **Committed in:** `cc0e5ee24`

**2. [Rule 4-adjacent, documented not changed] Confirm's render condition makes the UI-SPEC's E7 "all four actions co-render" scenario unreachable in the achievable state space**
- **Found during:** Task 2, while wiring the fixed-order action row
- **Issue:** The inherited context marked "Confirm is rendered only for constituents flagged by the needs_review leg... still in force" as a hard carry-forward from the Wave 1 tracer feedback gate. Under that rule (`person_id !== null && review_state === 'needs_review'`) combined with Re-flag's rule (`review_state ∈ {operator_confirmed, operator_edited}`), Confirm and Re-flag can never co-render on the same constituent — `review_state` is a single value, so a row cannot simultaneously BE `needs_review` (required for Confirm) and BE `operator_confirmed`/`operator_edited` (required for Re-flag). The maximum achievable co-render is therefore 3 actions (Confirm-as-unattributable + Edit + Re-flag, or Confirm + Confirm-as-unattributable + Edit), not the 4 the UI-SPEC's planner-resolved E7 example describes ("an unresolved-speaker constituent that has already been confirmed genuinely co-renders all four actions").
- **Not changed:** honoring the inherited "still in force" directive over the UI-SPEC's own illustrative (and, on inspection, internally inconsistent) example. `flex-wrap: wrap` is applied to the action row regardless, so the achievable 2-3-action case never overflows at 860px — the layout requirement E7 actually cares about is satisfied either way.
- **Files modified:** none beyond the action row itself (`app/src/routes/admin/review/+page.svelte`)
- **Verification:** `grep -c 'flex-wrap: wrap'` on the review page is 5 (includes both the filter row and the action row); the contract module asserts `flex-wrap: wrap` appears at least twice.
- **Impact:** Purely a documentation/interpretation note — no code needed to change to satisfy either reading, since the flex-wrap requirement holds regardless of how many actions actually co-render.

### Documented, Not Fixed (carried forward, not this plan's scope)

**3. Frontend `readonlyMode` flag split — still NOT done**
- Flagged by plan 49-04 as left open for this plan or a dedicated follow-up: `app/src/routes/admin/pipeline/[job_id]/+page.server.ts:294` still computes `readonlyMode = argument.status !== 'candidate'`, gating BOTH the Resolve card (49-04's now-widened backend concern) AND the unrelated `ArgumentDetailsCard` metadata-edit form behind one shared flag.
- **Not fixed here** — this plan's `files_modified` list does not include `admin/pipeline/[job_id]/+page.server.ts`, and splitting the flag is a small architectural change outside Task 1/2/3's explicit scope (queue queries, the queue screen, the source contract). Carried forward explicitly, not silently dropped, per this plan's environment notes.
- **Impact:** No behavior on this plan's own deliverables depends on this. Still an open item for a future plan or dedicated follow-up.

---

**Total deviations:** 1 auto-fixed (plan-text-vs-source mismatch on Person provenance format), 1 documented interpretation (E7's illustrative scenario vs. the inherited "still in force" Confirm rule), 1 carried-forward open item (readonlyMode split, explicitly not this plan's scope).
**Impact on plan:** No scope creep; no regression. All three are recorded rather than silently resolved or silently dropped.

## Issues Encountered

**Could not complete the Task 2 `<human-check>` browser walkthrough.** Same credential-access constraint recorded in 49-01-SUMMARY.md and 49-03-SUMMARY.md: authenticating to `/admin/**` requires `ADMIN_USERNAME`/`ADMIN_PASSWORD` (or `SESSION_SECRET` to forge a session cookie) from `.env`, and this sandbox's permission policy denies reading `.env`. Per this org's credential-handling posture, no workaround was attempted. Instead:

- Ran the full pytest suite (1403 passed, 5 xfailed, 0 failed) and `npm --prefix app run check` (0 errors, 37 warnings, unchanged baseline).
- Confirmed via `curl` against the live FastAPI dev server that all three filter axes (individually and combined), the unrecognised-value-applies-no-filter case, and `/api/admin/review/stats` behave exactly as specified.
- Confirmed via unauthenticated `curl` against the SvelteKit dev server that `/admin/review` and `/admin` both return `302` (session-gated redirect), never a `500`, after the route changes.
- Read every diff line-by-line against the plan's Screen Contract and UI-SPEC before committing.

**A human operator should complete the Task 2 seven-item `<human-check>` walkthrough before this plan is considered UAT-complete** — recorded as `human_judgment: true` on coverage items D4 and D5 above, not silently marked done.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- REVIEW-03 and REVIEW-04 remain `Pending` in `.planning/REQUIREMENTS.md` — both are shared with 49-06 (not yet complete) per the shared-ID gate (`requirements.ready-ids` returned `0/2 ready`, blocked on `["REVIEW-03", "REVIEW-04"]`). No action taken; correct per protocol.
- The `readonlyMode` split (49-04's carried-forward item) remains open — still not this plan's scope; left for 49-06 or a dedicated follow-up.
- **Open item for a human:** complete the Task 2 `<human-check>` seven-item browser walkthrough at `/admin/review` and `/admin` (tab switching, filter composition/back-button/active-filter-indicator, expand/collapse including the zero-constituent blockers fallback, Confirm/Confirm-as-unattributable/Re-flag acting on the right row with D-26's stay-visible behavior, all five dashboard StatCards in one even row, the StatCard's singular/zero-state link text, and no horizontal scroll at 375px) — blocked on this environment lacking authenticated browser access, not on any known defect.
- `api/domain/trust.py` confirmed byte-identical throughout this plan (`git diff --stat api/domain/trust.py` empty). `api/domain/authority.py` confirmed to import nothing beyond its own dependencies (no `fastapi`/`sqlalchemy`/`alembic` import). No new migration authored — `alembic/versions/` still ends at `0029`.
- Plan 49-06 can proceed against a fully built, tested `/admin/review` screen and backend.

## Self-Check: PASSED

- `api/tests/test_phase49_review_ui_contract.py` confirmed present via `git show cc0e5ee24 -- api/services/admin_review.py`-equivalent checks and direct `[ -f ]` test.
- Commits `cc0e5ee24`, `562f26c19`, `e731fb38e` all found in `git log --oneline --grep="49-05"`.
- `./.venv/bin/python -m pytest api/tests/test_admin_review_service.py -q` → 28 passed.
- `./.venv/bin/python -m pytest api/tests/test_phase49_review_ui_contract.py -q` → 14 passed.
- `./.venv/bin/python -m pytest -q` (full suite) → 1403 passed, 5 xfailed, 0 failed.
- `python3 -m compileall -q pipeline api scripts tests alembic` → clean.
- `npm --prefix app run check` → 0 errors, 37 warnings (same baseline as 49-03/49-04).
- `git diff --stat api/domain/trust.py` → empty.
- Spot-check of the E1 backstop test tripwire (deleted the `n === 1` singular branch, confirmed `test_backstop_E1_attention_count_keys_singular_plural_on_strict_equality_one` fails, reverted, confirmed clean `git diff`) → PASSED.
- `curl` against the live dev servers for the three filter axes, `/api/admin/review/stats`, and unauthenticated `302` responses on `/admin/review` and `/admin` → all as specified.

---
*Phase: 49-review-model*
*Completed: 2026-08-23*
