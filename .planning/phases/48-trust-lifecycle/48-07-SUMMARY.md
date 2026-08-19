---
phase: 48-trust-lifecycle
plan: 07
subsystem: api
tags: [fastapi, pydantic, sqlalchemy, trust-tier, publish-gate, audit-log]

requires:
  - phase: 48-trust-lifecycle
    plan: 01
    provides: "api.services.trust.recompute_argument_tier/summarize_tier_blockers/TrustGateBlocked and the argument_status_log.override_reason/.trust_tier_at_transition columns (migration 0027)"
  - phase: 48-trust-lifecycle
    plan: 02
    provides: "delete_argument's argument_status_log cascade fix, settled and untouched by this plan"
  - phase: 48-trust-lifecycle
    plan: 03
    provides: "the public trust leak-ban contract, including the previously-failing test_admin_detail_contract_does_declare_trust_tier this plan turns green"
provides:
  - "publish_argument(db, argument_id, override_reason=None) — the two-gate publish (non-overridable resolved_at gate, then the overridable UNCERTAIN trust gate) with a server-authoritative blank-reason check"
  - "PublishRequest — the one-field allow-list body for POST /arguments/{id}/publish"
  - "ArgumentDetail.trust_tier and StatusLogEntry.override_reason/.trust_tier_at_transition on the admin detail contract"
  - "structured 422 codes uncertain_tier_blocked and blank_override_reason on the publish route"
  - "unpublish_argument and update_participant_side now recompute the tier in-transaction before their own commit"
affects: ["49 (review queue) — inherits the working trust_tier field on ArgumentDetail and the blocked-publish payload shape for its own UI"]

actuals:
  tokens: 13853
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Tagged ValueError strings distinguished inside a single except ValueError handler (blank_override_reason vs. the pre-existing plain-string messages) rather than a second except clause, since Python cannot dispatch two handlers on the same exception type — the router inspects str(exc) to pick the response shape"
    - "TrustGateBlocked caught before the bare ValueError fallthrough (it subclasses ValueError) — same ordering discipline as DuplicateArgumentError's existing 409 mapping, now asserted by an AST criterion so a future reorder fails the build (T-48-SWALLOW)"

key-files:
  created: []
  modified:
    - api/services/admin_arguments.py
    - api/schemas/admin_arguments.py
    - api/routers/admin.py
    - api/tests/test_published_gate.py
    - api/tests/test_admin_arguments_routes.py
    - api/tests/test_admin_arguments_service.py

key-decisions:
  - "Three pre-existing zero-constituent publish tests in test_admin_arguments_service.py (predating Phase 48) now hit the new UNCERTAIN gate by construction (floor_tier's zero-constituent base case) — adapted them to pass a fixed override_reason rather than seed full trust-derivation fixtures, since their own purpose (audit-log row count, re-publish status transitions) is orthogonal to trust-tier coverage, which test_published_gate.py owns."
  - "The blank-reason ValueError and the pre-existing resolve-gate/already-published ValueErrors share one except ValueError handler in the router, distinguished by inspecting str(exc) — Python does not allow two except clauses on the same concrete exception type, so this is the only way to keep the two pre-existing messages byte-identical while adding the new structured blank-reason mapping."

requirements-completed: [TRUST-04, TRUST-05]

coverage:
  - id: D1
    description: "publish_argument evaluates the non-overridable resolved_at gate strictly before the overridable UNCERTAIN trust gate, in both the source (AST/line-index assertions) and behaviorally (an unresolved, uncertain-tier argument is blocked by the resolve gate regardless of override_reason)."
    requirement: "TRUST-04"
    verification:
      - kind: unit
        ref: "api/tests/test_published_gate.py::TestPublishOverrideGateSourceLevel::test_resolve_gate_precedes_trust_gate_in_publish_argument"
        status: pass
      - kind: integration
        ref: "api/tests/test_published_gate.py::test_publish_blocked_when_resolve_incomplete_even_with_override_reason"
        status: pass
    human_judgment: false
  - id: D2
    description: "A blocked publish (UNCERTAIN tier, no usable reason) raises TrustGateBlocked carrying the tier plus a non-empty, structured blocker breakdown (not a bare tier name), and writes nothing — published_at stays NULL, status is unchanged, no ArgumentStatusLog row is added."
    requirement: "TRUST-04"
    verification:
      - kind: integration
        ref: "api/tests/test_published_gate.py::test_publish_blocked_when_uncertain_without_reason"
        status: pass
    human_judgment: false
  - id: D3
    description: "An override reason that is empty, missing, or whitespace-only (including a non-breaking space) is rejected server-side after .strip(), independently of any UI affordance, with a distinguishable blank_override_reason code separate from the no-reason-supplied TrustGateBlocked case."
    requirement: "TRUST-05"
    verification:
      - kind: integration
        ref: "api/tests/test_published_gate.py::test_publish_blocked_when_override_reason_is_whitespace_only (4 parametrized whitespace forms)"
        status: pass
    human_judgment: false
  - id: D4
    description: "A successful override writes its ArgumentStatusLog row with override_reason set to the stripped text and trust_tier_at_transition set to the tier at that moment; a normal publish of a non-uncertain argument with no reason leaves both columns NULL — the override path is not accidentally mandatory."
    requirement: "TRUST-05"
    verification:
      - kind: integration
        ref: "api/tests/test_published_gate.py::test_publish_succeeds_with_override_and_logs_reason_and_tier, test_publish_without_override_leaves_audit_columns_null"
        status: pass
    human_judgment: false
  - id: D5
    description: "The override is per publish attempt and never sticky — an unpublish then a republish while still UNCERTAIN is blocked again and requires a fresh reason, writing a second distinct override log row; no persistent per-argument exemption flag exists anywhere in the schema or service."
    requirement: "TRUST-05"
    verification:
      - kind: integration
        ref: "api/tests/test_published_gate.py::test_override_is_not_sticky_across_republish"
        status: pass
      - kind: other
        ref: "grep -rn \"exemption|override_sticky|publish_override_flag\" api/ --include=*.py returns no lines"
        status: pass
    human_judgment: false
  - id: D6
    description: "GET /api/admin/arguments/{id} returns trust_tier; the admin list endpoints are untouched; trust_tier never appears in any public response."
    requirement: "TRUST-04"
    verification:
      - kind: unit
        ref: "api/tests/test_trust_public_leak_ban.py::test_admin_detail_contract_does_declare_trust_tier (now passing — the target this plan turns green) and the existing public leak-ban tests (unmodified, still green)"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_arguments_routes.py::test_publish_route_with_override_reason_returns_200_and_trust_tier"
        status: pass
    human_judgment: false
  - id: D7
    description: "publish_argument, unpublish_argument, and update_participant_side each recompute the tier in their own transaction before their own commit — the tier stays live after publish/unpublish/participant edits."
    requirement: "TRUST-02"
    verification:
      - kind: unit
        ref: "api/tests/test_published_gate.py::TestPublishOverrideGateSourceLevel::test_publish_argument_recomputes_tier_before_committing, test_unpublish_and_participant_side_update_recompute_before_committing"
        status: pass
    human_judgment: false
  - id: D8
    description: "The blocked-publish payload's structure is rich enough for Phase 49's review queue to reuse without re-deriving it."
    verification: []
    human_judgment: true
    rationale: "Flagged in 48-07-PLAN.md's <flagged_assumptions> as a backstop-only claim — Phase 49's review queue does not exist yet, so no automated evidence can prove this phase's payload shape (code/trust_tier/blockers/message) will be reused as-is. Abstains to human review at Phase 49 planning time, per the plan's own documented abstention."

duration: ~45min
completed: 2026-08-19
status: complete
---

# Phase 48 Plan 07: Two-Gate Publish, Overridable Trust Gate, and Audit Record Summary

**Turns the single `published_at` promotion into two distinct gates — a non-overridable `resolved_at IS NULL` completeness check and an overridable UNCERTAIN trust-tier check — with a server-authoritative required-reason override permanently recorded on the `ArgumentStatusLog` row the transition already writes, and exposes `trust_tier` on the admin-only detail contract.**

## Performance

- **Duration:** ~45 min
- **Tasks:** 3/3 complete
- **Files modified:** 6

## Accomplishments

- `api/services/admin_arguments.py::publish_argument` gained `override_reason: str | None = None`. The two pre-existing guards (`resolved_at IS NULL`, already-PUBLISHED) keep their exact position and wording; after them, the tier is recomputed fresh via `recompute_argument_tier` and, only if it reads `UNCERTAIN`, the publish is blocked by `TrustGateBlocked` (carrying the tier plus `summarize_tier_blockers`' breakdown) unless a non-blank reason is supplied — a supplied-but-blank reason raises a distinguishable tagged `ValueError("blank_override_reason")` instead of silently re-showing the block. The same `ArgumentStatusLog` row the publish already writes now carries `override_reason`/`trust_tier_at_transition` when the override path was taken, and stays NULL in both columns otherwise.
- `unpublish_argument` and `update_participant_side` each gained an `await recompute_argument_tier(db, argument_id)` call before their own existing commit (D-08; the participant-side call site is a deliberate no-op today per D-10, landing ahead of Phase 49's `review_state` column).
- `get_argument_detail` now returns `trust_tier` and extends each `status_log` entry with `override_reason`/`trust_tier_at_transition`.
- `api/schemas/admin_arguments.py` gained `PublishRequest` (a one-field allow-list, mirroring `ArgumentUpdate`'s mass-assignment discipline — T-48-MASS), `ArgumentDetail.trust_tier` (defaulting to `TrustTier.UNCERTAIN`), and `StatusLogEntry.override_reason`/`.trust_tier_at_transition`.
- `api/routers/admin.py`'s publish route accepts an optional `PublishRequest` body (absent body ⇒ `override_reason=None`, matching the SvelteKit action's current no-body POST), catches `TrustGateBlocked` before the bare `ValueError` fallthrough (it subclasses `ValueError` — T-48-SWALLOW, now locked by an AST handler-ordering assertion), and maps it plus the blank-reason case to structured 422 detail dicts (`uncertain_tier_blocked`, `blank_override_reason`) while the two pre-existing plain-string 422 messages stay byte-identical.
- Corrected three remaining stale "pipeline"/"PIPELINE status" docstring references (`list_arguments`, `get_argument_stats`, `update_resolve_row`'s route docstring, and the list route's `valid_status_values` explanation) to name the `candidate` born state (Phase 48 D-01/D-04) — no query or gate behavior changed, wording only.
- Added 6 named DB-gated tests plus 3 source-level tests to `test_published_gate.py` covering both gate-ordering edges (TRUST-04/TRUST-05 unclassified probe rows), the whitespace-only reason rejection (4 parametrized forms including a non-breaking space), the audit-row contents on both the override and non-override paths, and non-stickiness across unpublish/republish.
- Added 8 route-level tests to `test_admin_arguments_routes.py`: an auth test proving the new body parameter doesn't bypass the router-level dependency, 4 monkeypatched structured/plain 422-mapping tests, and 2 DB-gated end-to-end tests (200 + `trust_tier` in the response; extra body keys have no effect).
- Adapted 3 pre-existing zero-constituent publish tests in `test_admin_arguments_service.py` (see Deviations) so the full suite stays green under the new gate.

## Task Commits

Each task was committed atomically:

1. **Task 1: The two-gate publish, the validated override, and the extended audit row** - `09143ac4b` (feat)
2. **Task 2: Request/response contract and the structured 422 mapping** - `0e15d547e` (feat)
3. **Task 3: Gate, override, and non-stickiness coverage** - `9373ef7ff` (test)

**Plan metadata:** (this commit) — `docs(48-07): complete plan`

## Files Created/Modified

- `api/services/admin_arguments.py` - Two-gate `publish_argument` (Task 1), recompute calls in `unpublish_argument`/`update_participant_side` (Task 1), `trust_tier`/audit columns on `get_argument_detail` (Task 1), corrected docstrings (Task 1)
- `api/schemas/admin_arguments.py` - `PublishRequest`, `ArgumentDetail.trust_tier`, `StatusLogEntry` audit fields (Task 2)
- `api/routers/admin.py` - Publish route body parameter, structured 422 mapping, corrected docstrings (Task 2)
- `api/tests/test_published_gate.py` - Source-level + DB-gated gate/override/audit/non-stickiness coverage (Task 3)
- `api/tests/test_admin_arguments_routes.py` - Auth, structured-422, and end-to-end publish route coverage (Task 3)
- `api/tests/test_admin_arguments_service.py` - Adapted 3 pre-existing zero-constituent publish tests to pass an override reason (Task 1 deviation)

## Decisions Made

- Kept the two pre-existing gates (`resolved_at IS NULL`, already-PUBLISHED) in their exact original position and error text — the trust gate is inserted strictly after both, so D-14's "which wall did I hit" guarantee holds for every combination the acceptance criteria probe.
- `PublishRequest` carries no Pydantic validator for the blank-reason case, per the plan's explicit instruction — that check is a service-layer concern (D-17) so a direct API call and the future admin UI see the identical rejection, with the service's own tagged code surfacing through the router rather than a generic Pydantic 422.
- The router's blank-reason and pre-existing-message ValueErrors share a single `except ValueError` handler (see key-decisions above) — Python cannot dispatch two handlers on the same exception class, so distinguishing them requires inspecting `str(exc)` inside one handler rather than the plan prose's literal "then catch ... then catch" phrasing, which is a two-if-branches-in-one-except pattern, not two separate `except` clauses.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug in pre-existing tests] Three zero-constituent publish tests now require an override reason**
- **Found during:** Task 1, verifying `api/tests/test_admin_arguments_service.py` against the new gate
- **Issue:** `test_publish_argument_from_draft_writes_one_published_log_row`, `test_unpublish_then_republish_succeeds_and_preserves_published_at`, and `test_get_argument_detail_includes_status_log_and_speakers` (all pre-dating Phase 48) seed an `Argument` with zero utterances and zero (or only resolved) participants. Per D-13's zero-constituent base case, `floor_tier([])` is `UNCERTAIN`, so these three tests' unconditional `publish_argument(db, arg_id)` calls now hit the new trust gate and raise `TrustGateBlocked` instead of succeeding — a correctness consequence of Task 1's own required change, not a bug introduced elsewhere.
- **Fix:** Passed a fixed `override_reason="pre-existing test override"` to each affected `publish_argument()` call. None of the three tests assert anything about the audit columns' contents (they only assert `status`/`published_at`/log-row-count), so this is a minimal, assertion-preserving fix; the canonical coverage for override-column contents and the zero-reason non-uncertain case lives in Task 3's new `test_published_gate.py` tests.
- **Files modified:** `api/tests/test_admin_arguments_service.py`
- **Verification:** `./.venv/bin/python -m pytest api/tests/test_admin_arguments_service.py api/tests/test_published_gate.py -q` — 89 passed.
- **Committed in:** `09143ac4b` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (test adaptation, no production-code change beyond what the plan itself specified)
**Impact on plan:** No scope creep — the fix only touches test seeding/call-sites in a file the plan did not list under `files_modified` but which is directly, foreseeably impacted by the plan's own required service-layer change.

## Issues Encountered

None beyond the deviation above. One transient issue during verification: a mid-session test failure (unrelated to this plan's logic — a stale grep match on the word "exemption" inside my own explanatory code comment, which I reworded) left dirty rows in `TEST_DATABASE_URL` from an earlier `test_admin_arguments_service.py` run that failed before its cleanup block executed; cleaned up manually before re-running, no lasting effect.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `trust_tier` and the two audit columns are live on `ArgumentDetail`/`StatusLogEntry` — Phase 49's review queue can read them without any new endpoint or schema work (D-20).
- The blocked-publish payload shape (`code`, `trust_tier`, `blockers`, `message`) is available for Phase 49's queue to reuse as-is; whether it does so cleanly is the plan's own flagged backstop-only truth (D8 above), not yet verifiable since that phase doesn't exist.
- Full suite (`api/tests pipeline/tests tests`): 1166 passed, 5 xfailed, 0 failed — up from the 1146 passed / 1 failed (the target D-20 test) baseline this plan inherited. No other regressions; the shared dev-DB row-count tripwire stayed clean throughout.
- `.planning/WINDOWS.md` entry #6 (the D-20 unmet-truth tracked from plan 48-03) marked `fixed`.

## Self-Check: PASSED

- FOUND: api/services/admin_arguments.py (modified)
- FOUND: api/schemas/admin_arguments.py (modified)
- FOUND: api/routers/admin.py (modified)
- FOUND: api/tests/test_published_gate.py (modified)
- FOUND: api/tests/test_admin_arguments_routes.py (modified)
- FOUND: api/tests/test_admin_arguments_service.py (modified)
- FOUND commit: 09143ac4b
- FOUND commit: 0e15d547e
- FOUND commit: 9373ef7ff

---
*Phase: 48-trust-lifecycle*
*Completed: 2026-08-19*
