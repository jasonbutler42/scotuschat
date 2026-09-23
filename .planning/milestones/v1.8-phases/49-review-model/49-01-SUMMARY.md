---
phase: 49-review-model
plan: 01
subsystem: review-model
tags: [postgresql-enum, alembic, fastapi, sveltekit, trust-tier, admin-review]

requires:
  - phase: 48-trust-model
    provides: "TrustTier / derive_tier / floor_tier / recompute_argument_tier domain and service layer, with the D-13 participant slot left un-fed"

provides:
  - "review_state PG enum (4 permanent values) + argument_participants.review_state/source/method columns (migration 0028)"
  - "ValueDiscrepancy model + value_discrepancy table (schema only — no writer/reader yet; plans 49-02+ populate it)"
  - "_load_constituents feeding derive_tier real per-participant (source, method, review_state) values (D-18)"
  - "api/services/admin_review.py: list_review_queue_arguments, resolve_participant_review"
  - "GET /api/admin/review/arguments, PATCH /api/admin/review/participants/{id}"
  - "/admin/review SSR screen: minimal queue table with inline Confirm and a Resolve-speaker deep link"
  - "REVIEW-01 schema contract test (api/tests/test_review_state_schema.py)"

affects: [49-02-person-review-fold, 49-04-authority-ladder, 49-05-review-ui]

actuals:
  tokens: 20924
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "One public service entry point commits exactly once at the end; helpers it composes never commit (verified against api/services/admin_arguments.py, contradicts 49-RESEARCH.md's 'caller commits' claim)"
    - "Correlated scalar subquery (not a join) to attach a nullable most-recent-child-id onto a one-row-per-parent query without multiplying rows"

key-files:
  created:
    - alembic/versions/0028_review_state_and_discrepancy.py
    - api/services/admin_review.py
    - api/schemas/admin_review.py
    - api/routers/admin_review.py
    - app/src/routes/admin/review/+page.server.ts
    - app/src/routes/admin/review/+page.svelte
    - api/tests/test_admin_review_service.py
    - api/tests/test_review_state_schema.py
  modified:
    - api/models/models.py
    - api/services/trust.py
    - api/main.py
    - app/src/routes/admin/arguments/+page.svelte
    - app/src/routes/admin/arguments/[id]/+page.svelte

key-decisions:
  - "review_state PG enum minted with exactly 4 permanent values (unreviewed, needs_review, operator_confirmed, operator_edited) — decision gate resolved by human, option 'four-values-as-specified'"
  - "Migration split into 0028 (this plan) + 0029 (plan 49-02) so no consumer is ever broken mid-repo"
  - "Confirm is scoped to review_state==needs_review only; clearing an unresolved (person_id IS NULL) row is plan 49-04's 'confirm as unattributable' action, not this one"
  - "Pulled forward one piece of 49-05's already-decided routing (admin_job_id -> /admin/pipeline/{job_id} deep link) because the tracer was otherwise a dead end on the only unresolved data that exists in the live DB"

patterns-established:
  - "Deterministic ordering: any queue-style listing that mixes an outer-joined child collection must order by an immutable child key (side, id), never rely on physical/scan order, or an UPDATE silently reorders the child on its own row"

requirements-completed: [REVIEW-01, REVIEW-03, REVIEW-04]

coverage:
  - id: D1
    description: "review_state PG enum (4 permanent values) + argument_participants.review_state/source/method columns, migration 0028"
    requirement: "REVIEW-01"
    verification:
      - kind: integration
        ref: "api/tests/test_review_state_schema.py#test_review_state_pg_enum_has_exactly_four_values"
        status: pass
      - kind: integration
        ref: "api/tests/test_review_state_schema.py#test_argument_participants_review_state_source_method_columns"
        status: pass
      - kind: integration
        ref: "api/tests/test_review_state_schema.py#test_insert_without_review_state_defaults_to_unreviewed"
        status: pass
      - kind: integration
        ref: "api/tests/test_review_state_schema.py#test_python_review_state_enum_matches_pg_enum"
        status: pass
    human_judgment: false
  - id: D2
    description: "_load_constituents feeds derive_tier real per-participant (source, method, review_state) values instead of contributing nothing (D-18)"
    requirement: "REVIEW-04"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_review_service.py#test_patch_confirm_advances_review_state_and_recomputes_tier"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_review_service.py#test_recompute_zero_constituents_stores_uncertain_no_exception"
        status: pass
    human_judgment: false
  - id: D3
    description: "GET /api/admin/review/arguments (D-05 OR-composed inclusion query, one row per argument) and PATCH /api/admin/review/participants/{id} confirm action"
    requirement: "REVIEW-03"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_review_service.py#test_get_review_queue_returns_flagged_argument_once_with_constituent"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_review_service.py#test_list_review_queue_returns_200_and_excludes_healthy_argument"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_review_service.py#test_patch_confirm_missing_participant_returns_404"
        status: pass
    human_judgment: false
  - id: D4
    description: "Tracer feedback gate defect 1 fix — deterministic constituent ordering (side, id) so a confirmed row never moves in the list"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_review_service.py#test_constituent_order_is_stable_across_an_update"
        status: pass
    human_judgment: false
  - id: D5
    description: "Tracer feedback gate defect 2a fix — Confirm rendered only for needs_review constituents; backend rejects (422) a confirm on a person_id-IS-NULL participant"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_review_service.py#test_patch_confirm_rejects_unresolved_speaker"
        status: pass
    human_judgment: false
  - id: D6
    description: "Tracer feedback gate defect 2b fix — queue payload carries admin_job_id (correlated subquery, no row multiplication); /admin/review renders a 'Resolve speaker' link to /admin/pipeline/{admin_job_id} (falling back to /admin/arguments/{id}) for an unresolved constituent"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_review_service.py#test_queue_payload_admin_job_id_none_when_unlinked"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_review_service.py#test_queue_payload_admin_job_id_populated_and_does_not_duplicate_constituents"
        status: pass
    human_judgment: true
    rationale: "Backend behavior (admin_job_id population, non-multiplication) is fully unit/integration-tested. The rendered Svelte conditional (Confirm button vs. 'Resolve speaker' link, correct href) has not been re-verified in a live browser since this fix — the original tracer feedback gate that caught defects 1/2 was itself a human browser check, and this fix has not yet gone through an equivalent second round."

duration: 45min
completed: 2026-08-23
status: complete
---

# Phase 49 Plan 01: Review-Model Tracer Summary

**End-to-end participant review tracer (migration 0028, `/admin/review` queue + Confirm) shipped, then repaired at the tracer feedback gate: deterministic constituent ordering, Confirm scoped to resolved speakers only, and an unresolved speaker's real fix routed through a "Resolve speaker" deep link to the existing `/admin/pipeline/{job_id}` person-search flow.**

## Performance

- **Tasks:** 2 (Task 1 tracer + Task 1b defect-fix pass, Task 2 schema contract test)
- **Commits:** 3
- **Files touched:** 14 (7 created new in this plan's defect-fix/test pass, plus the original tracer's files)

## Accomplishments

- Migration `0028` mints the permanent 4-value `review_state` PG enum and adds `argument_participants.review_state/source/method`, plus the new (as-yet-unused) `value_discrepancy` table.
- `api/services/trust.py::_load_constituents` now calls `derive_tier` with each participant's real `(source, method, review_state)` instead of contributing nothing for a resolved participant (D-18).
- `/admin/review` lists every argument needing operator attention via a single OR-composed D-05 query, and one inline Confirm action advances a `needs_review` participant to `operator_confirmed`, recomputing the argument's `trust_tier` in the same transaction.
- **Tracer feedback gate (human browser test) found two real defects, both fixed in this plan, not deferred:**
  1. **Non-deterministic ordering** — a confirmed constituent visibly jumped to the bottom of its argument's row because the query had no ordering key on the participant. Fixed by adding `ArgumentParticipant.side`, `ArgumentParticipant.id` ascending to the existing `ORDER BY` chain.
  2. **Confirm was a permanent no-op on every flagged row that actually exists in the live DB** — all 11 flagged constituents on argument 1788 are flagged by the unresolved-speaker leg (`person_id IS NULL`), which Confirm never touches. Fixed in three parts: Confirm now renders/accepts only for a `needs_review` constituent; an unresolved constituent gets a "Resolve speaker →" link to `/admin/pipeline/{admin_job_id}` (falling back to `/admin/arguments/{argument_id}`), pulling forward one piece of plan 49-05's already-decided routing because the tracer would otherwise be a dead end; the queue payload now carries `admin_job_id` via a correlated scalar subquery that cannot multiply an argument's constituent rows.
- REVIEW-01's schema contract is now a named, automated, spot-checked test (`api/tests/test_review_state_schema.py`) — verified to fail if the `review_state` server_default is removed from the model.

## Task Commits

Each task/segment was committed atomically:

1. **Task 1 — tracer:** `299a25427` (feat) — migration 0028, `ReviewState` + provenance columns, `_load_constituents` real values, `/admin/review` + confirm end-to-end. *(committed before this continuation started; resumed here after the human's tracer feedback gate.)*
2. **Task 1b — tracer feedback gate defect fixes:** `9d2b55400` (fix) — deterministic constituent ordering; Confirm scoped to `needs_review`; unresolved constituents get a "Resolve speaker" deep link backed by a new `admin_job_id` field; stale `+page.server.ts` docstring corrected; three new regression tests.
3. **Task 2 — REVIEW-01 schema contract test:** `ce4943f8a` (test) — `api/tests/test_review_state_schema.py`, 4 tests, spot-checked against a deliberately broken `server_default`.

_No plan-metadata commit is issued separately in this SUMMARY step's own commit — the metadata/state/roadmap update below is folded into the final commit produced by this execution._

## Files Created/Modified

- `alembic/versions/0028_review_state_and_discrepancy.py` — mints `review_state`, three `argument_participants` columns, `value_discrepancy` table
- `api/models/models.py` — `ReviewState` enum, `ArgumentParticipant.review_state/source/method`, `ValueDiscrepancy` model
- `api/services/trust.py` — participant branch of `_load_constituents` now calls `derive_tier` with real values
- `api/services/admin_review.py` — `list_review_queue_arguments` (D-05 query, deterministic ordering, `admin_job_id` subquery), `resolve_participant_review` (unresolved-speaker guard)
- `api/schemas/admin_review.py` — `ReviewQueueConstituent`, `ReviewQueueArgumentItem` (+ `admin_job_id`), `ReviewActionRequest`
- `api/routers/admin_review.py` — `GET /arguments`, `PATCH /participants/{id}`, mounted in `api/main.py`
- `app/src/routes/admin/review/+page.server.ts` — SSR load + `confirm` form action, corrected docstring, `admin_job_id` in the item type
- `app/src/routes/admin/review/+page.svelte` — queue table; Confirm button only for `needs_review`; "Resolve speaker →" link for `person_id === null`
- `app/src/routes/admin/arguments/+page.svelte`, `app/src/routes/admin/arguments/[id]/+page.svelte` — one new `blockerSentence` branch for `uncertain_participant`
- `api/tests/test_admin_review_service.py` — 9 tests total: the plan's original 6 `<behavior>` bullets plus 3 new regression tests for the tracer feedback gate defects
- `api/tests/test_review_state_schema.py` — new, 4 tests, REVIEW-01 contract

## Decisions Made

- **review_state vocabulary locked at 4 permanent values** (decision gate, resolved by human before Task 1 ran): `unreviewed`, `needs_review`, `operator_confirmed`, `operator_edited`. PostgreSQL cannot drop an enum value — this is a one-way door, matching D-09.
- **Migration split (0028 here / 0029 in plan 49-02)** so the repo is never left broken mid-plan with `people.name_needs_review` dropped before its ~20 consumers are updated.
- **Commit convention corrected against source, not upstream docs:** `resolve_participant_review` commits exactly once at the end (mirrors `publish_argument`/`update_participant_side`), contradicting 49-RESEARCH.md's "caller commits" claim — direct inspection of `api/services/admin_arguments.py` won.
- **Confirm's scope was narrowed, not widened, in response to real data.** Rather than teaching Confirm to also clear `person_id` (an architectural change reserved for plan 49-04's "confirm as unattributable" action, D-17), the fix routes the unresolved case to the *existing* person-resolve flow instead.
- **admin_job_id pulled forward from plan 49-05's decision, not re-decided.** 49-05-PLAN.md already specifies `/admin/pipeline/{job_id}` with the `/admin/arguments/{id}` fallback for exactly this "person-link edit" case; this plan implements that decision one wave early because it is the only data path that makes the tracer's Confirm feature reachable at all against the live DB's actual 11 unresolved rows.

## Deviations from Plan

### Auto-fixed / Directed Issues

**1. [Rule 3 - Blocking, carried forward from Task 1] Plan's named verify module does not exist**
- **Found during:** Task 1 (original tracer commit, `299a25427`)
- **Issue:** The plan's `<verify>` block names `api/tests/test_trust_service.py`, which does not exist in this codebase.
- **Fix:** Ran the real modules that cover the same trust-domain surface instead: `api/tests/test_trust_domain.py`, `api/tests/test_trust_recompute.py`, `api/tests/test_trust_tracer.py`, `api/tests/test_trust_public_leak_ban.py`. Re-confirmed in this continuation session (all 147 tests across these plus `test_admin_arguments_service.py` pass).
- **Files modified:** none (verification-only substitution)
- **Verification:** `./.venv/bin/python -m pytest api/tests/test_trust_domain.py api/tests/test_trust_recompute.py api/tests/test_trust_tracer.py api/tests/test_trust_public_leak_ban.py api/tests/test_admin_arguments_service.py -q` → 147 passed
- **Committed in:** no code change; documented here and in Task 1's own SUMMARY-equivalent history

**2. [Rule 1 - Bug] Non-deterministic constituent ordering (tracer feedback gate defect 1)**
- **Found during:** human browser test of `/admin/review` after Task 1's tracer landed
- **Issue:** `list_review_queue_arguments`'s `ORDER BY` covered only `Argument.argued_date`/`Argument.id`; PostgreSQL rewrites an UPDATEd row as a new heap tuple, so a just-confirmed constituent surfaced last on the next scan — visibly "jumping to the bottom."
- **Fix:** Added `ArgumentParticipant.side.asc()`, `ArgumentParticipant.id.asc()` to the existing `ORDER BY` chain, after the unchanged argument-level keys.
- **Files modified:** `api/services/admin_review.py`
- **Verification:** `test_constituent_order_is_stable_across_an_update` — writes to one constituent, re-queries, asserts identical order
- **Committed in:** `9d2b55400`

**3. [Rule 2 - Missing Critical] Confirm was a permanent no-op on the only flagged data that exists (tracer feedback gate defect 2)**
- **Found during:** same human browser test — argument 1788's 11 constituents are all flagged via `person_id IS NULL`, never via `needs_review`; `resolve_participant_review` never wrote `person_id`, so Confirm could never clear that leg, and the screen offered no other way to resolve it.
- **Fix (three parts, exactly as specified, no architectural extension):** (a) Confirm button/accept path scoped to `review_state === 'needs_review'` only, with a server-side `person_id IS NULL` rejection (422) mirroring `update_participant_side`'s established rejection idiom; (b) a "Resolve speaker →" link to `/admin/pipeline/{admin_job_id}` (fallback `/admin/arguments/{argument_id}`) for an unresolved constituent, using 49-05-PLAN.md's already-decided routing; (c) the queue payload gained a per-argument `admin_job_id` (correlated scalar subquery — verified not to multiply constituent rows) and the stale `+page.server.ts` docstring was corrected.
- **Files modified:** `api/services/admin_review.py`, `api/schemas/admin_review.py`, `app/src/routes/admin/review/+page.server.ts`, `app/src/routes/admin/review/+page.svelte`
- **Verification:** `test_patch_confirm_rejects_unresolved_speaker`, `test_queue_payload_admin_job_id_none_when_unlinked`, `test_queue_payload_admin_job_id_populated_and_does_not_duplicate_constituents`
- **Committed in:** `9d2b55400`

---

**Total deviations:** 3 (1 carried-forward verify-module substitution, 1 Rule 1 bug fix, 1 Rule 2 missing-critical fix)
**Impact on plan:** All three were either already-scoped substitutions or explicitly directed, bounded fixes (no scope creep beyond what plan 49-05 had already decided). `api/domain/trust.py` remains byte-identical to its pre-Task-1 state throughout.

## Issues Encountered

None beyond the two tracer feedback gate defects documented above, both resolved in this session.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The participant half of the review model (REVIEW-01/03/04) is live, tested, and has survived one real human-in-the-browser feedback cycle.
- `value_discrepancy` table exists but is unpopulated — plans 49-02+ own writing/reading it.
- Plan 49-05's UI still needs to build the full queue screen (filters, tabs, People queue, discrepancy display) — this plan's `/admin/review` is deliberately a minimal subset.
- **Not yet re-verified in a live browser:** the Confirm-vs-Resolve-speaker-link conditional rendering (coverage item D6) was fixed and unit/integration-tested, but has not been walked through in a browser since the fix, unlike the original tracer. Recommend a quick human spot-check of `/admin/review` before this plan is considered fully closed at the UAT layer.

## Self-Check: PASSED

- `api/services/admin_review.py`, `api/schemas/admin_review.py`, `api/tests/test_admin_review_service.py`, `app/src/routes/admin/review/+page.server.ts`, `app/src/routes/admin/review/+page.svelte`, `api/tests/test_review_state_schema.py` — all exist on disk (confirmed via `git status`/`git show`).
- Commits `299a25427`, `9d2b55400`, `ce4943f8a` all found in `git log --oneline --grep="49-01"`.
- `api/domain/trust.py` confirmed byte-identical (`git diff --stat api/domain/trust.py` empty).
- `./.venv/bin/python -m pytest api/tests/test_admin_review_service.py api/tests/test_review_state_schema.py -q` → 13 passed.
- `./.venv/bin/python -m pytest api/tests/test_trust_domain.py api/tests/test_trust_recompute.py api/tests/test_trust_tracer.py api/tests/test_trust_public_leak_ban.py api/tests/test_admin_arguments_service.py -q` → 147 passed.
- `python3 -m compileall -q pipeline api scripts tests alembic` → clean.
- `npm run check` (svelte-check) → 0 errors (36 pre-existing warnings, none in this plan's files).
- Spot-check of REVIEW-01 test tripwire (removed `server_default`, confirmed failure, reverted, confirmed clean `git diff`) → PASSED.

---
*Phase: 49-review-model*
*Completed: 2026-08-23*
