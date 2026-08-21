---
phase: 48-trust-lifecycle
verified: 2026-08-21T17:20:00Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification: refreshed-docs-only
---

# Phase 48: Trust & Lifecycle Verification Report

**Phase Goal:** Materialized `trust_tier` rollup, `candidate`-on-arrival status, and a
single `published_at` promotion gate hard-blocked on UNCERTAIN with a logged operator
override.

**Verified:** 2026-08-21T15:14:12Z
**Status:** passed
**Re-verification:** Timestamp refreshed 2026-08-21T17:20:00Z — documentation-only.

> **Why this timestamp moved.** The original verification (2026-08-21T15:14:12Z, status
> `passed`, 5/5 must-haves) stands unchanged. During Phase 48 close-out, dated `CORRECTION`
> notes were appended to `48-08-SUMMARY.md` recording that WINDOWS.md entry #8 had been
> marked `fixed` on 2026-08-20 and confirmed live at 48-UAT.md test 6 — the entry's own
> description had contradicted its status. Committing that SUMMARY edit made its commit time
> newer than the verification, which the staleness check (#2348) correctly flagged as
> `stale`: it compares change times and cannot distinguish appended prose from a changed
> deliverable.
>
> No deliverable, test, or must-have changed. Full UAT is recorded complete at 65/65 in
> `48-UAT.md` (51 auto-covered by passing tests, 14 operator-confirmed), the one gap found
> (G-48-11) is resolved and re-verified, and the security review is clean (0 threats open).
> The timestamp is refreshed rather than the phase re-verified, and this note exists so the
> refresh is auditable rather than silent.

## Context for this report

This phase was declared "shipped" in STATE.md before this verification ran, and a
post-close-out code review (`48-REVIEW.md`) already found and fixed one genuine blocker
(the list-page `unpublish` action silently redirecting on failure) that all 10 execution
plans and 1209 pre-fix tests had missed. That history was treated as a reason for
heightened scrutiny, not as evidence of anything, per the verification brief. Every claim
below was re-derived from the codebase and from live command execution in this session,
not taken from SUMMARY.md or EVIDENCE.md narrative.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Every argument carries a `trust_tier` derived from provenance + review state by one documented function | VERIFIED | `api/domain/trust.py::derive_tier` is the sole mapping (grepped — no other implementation exists); native PG enum `trust_tier` added by migration 0027; `api/tests/test_trust_domain.py` (10 tests: exhaustive cross-product, precedence, fail-closed, permutation invariance) — ran directly, all passed |
| 2 | `trust_tier` is the floor (minimum) of utterances + participants, materialized and recomputed on every constituent change | VERIFIED | `api/domain/trust.py::floor_tier` (permutation-invariant `min()` over a fixed rank, explicit empty→UNCERTAIN); `api/services/trust.py::recompute_argument_tier` scoped to one `argument_id`, non-committing; traced every call site (`admin_arguments.py:665,786,828`; `admin_jobs.py:545,615,869,1027`; `import_convokit.py:653`; `ingest.py:573`; `parse.py:461`; `resolve.py:372`; `recompute_trust.py:90`) — each precedes its own writer's commit; ran `api/tests/test_trust_recompute.py` (18 passed) |
| 3 | A newly imported argument is born a `candidate` (not public) with its tier set on arrival | VERIFIED | `Argument.status` model default is `ArgumentStatusEnum.CANDIDATE` (`api/models/models.py:313`); corpus writer passes explicit `status=CANDIDATE` kwarg (required — explicit kwargs don't inherit a changed default) and logs a birth `ArgumentStatusLog` row before its own recompute call; PDF ingest deliberately omits the kwarg and relies on the default, also logs a birth row; live evidence in `48-EVIDENCE.md` §3 confirms both corpus fixtures (15169, 22372) landed at `candidate` with exactly one, oldest, born-state status-log row |
| 4 | Publishing while any UNCERTAIN element remains is hard-blocked at the single `published_at` gate | VERIFIED | `publish_argument` (`api/services/admin_arguments.py:602-716`) evaluates `resolved_at IS NULL` first (non-overridable), then already-PUBLISHED, then recomputes the tier and raises `TrustGateBlocked` when UNCERTAIN with no reason — confirmed by reading the function in full: `override_reason` is never referenced before both prior guards return/raise; `api/tests/test_published_gate.py` (31 tests) ran directly and passed |
| 5 | Operator can override the publish block with a deliberate, logged, per-argument acknowledgment | VERIFIED | A non-blank `override_reason` (server-side `.strip()`, independent of client) unblocks publish and writes `ArgumentStatusLog.override_reason` + `.trust_tier_at_transition`; override is per-attempt only — no persistent flag exists anywhere in the schema (grepped models.py); UI on both `/admin/arguments/[id]` (48-08) and `/admin/arguments` (48-10) relays this without re-implementing the gate; `api/tests/test_admin_arguments_routes.py`, `test_phase48_publish_override_ui_contract.py`, `test_phase48_list_publish_override_ui_contract.py` all ran directly and passed |

**Score:** 5/5 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `api/domain/trust.py` | pure `derive_tier`/`floor_tier`, no framework imports | VERIFIED | Read in full; zero FastAPI/SQLAlchemy/Alembic imports; `test_domain_trust_module_has_no_framework_imports` passes |
| `api/services/trust.py` | `recompute_argument_tier`, `TrustGateBlocked`, `summarize_tier_blockers` | VERIFIED | Read in full; non-committing UPDATE with `synchronize_session=False`; D-10/D-11/D-12 rules implemented exactly as specified |
| `alembic/versions/0027_trust_tier_and_candidate_status.py` | candidate enum value, trust_tier column, override columns, in 5 correctly-ordered steps | VERIFIED | Read in full; `alembic current` confirms `0027 (head)` on the dev DB |
| `api/services/admin_arguments.py::delete_argument` | argument_status_log cascade step | VERIFIED | `delete(ArgumentStatusLog)` present before `delete(Argument)`; regression tests `test_delete_argument_cascades_argument_status_log` / `_multiple_status_log_rows` ran directly and passed |
| `api/tests/test_trust_public_leak_ban.py` | structural + live public-leak ban | VERIFIED | Ran directly (11 tests passed); independently confirmed by grepping `api/schemas/{cases,people,utterance,speakers}.py` and all three public routers/services for `trust_tier` — zero hits |
| `pipeline/commands/recompute_trust.py` | offline drift-repair + verification CLI | VERIFIED | Reads via `api.services.trust.recompute_argument_tier`; `pipeline/__main__.py` wires it; `EVIDENCE.md`'s reported `4 scanned, 0 changed` transcript is consistent with the writer wiring independently traced above |
| List-page + detail-page admin UI | block-reason panel, override field, per-row tier badge | VERIFIED | Both `+page.server.ts` files and both `+page.svelte` files read in full; `res.ok` checked before every redirect in both `publish` and `unpublish` actions (post-CR-01 fix); tier badge helpers present and wired to `arg.trust_tier` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `recompute_argument_tier` | every writer's own `db.commit()` | in-transaction call ordering | WIRED | Traced all 12 non-test call sites; each precedes its writer's commit (API services) or sits inside `get_session()`'s commit-on-exit block (pipeline commands) |
| `publish_argument`/`unpublish_argument` | `get_argument_detail` re-read | `db.refresh(argument)` after bulk `update()` | WIRED | Both functions refresh the loaded ORM object post-commit before re-reading, avoiding the Phase 31 stale-identity-map bug |
| List-page `unpublish` action | `res.ok` check | CR-01 fix | WIRED | `app/src/routes/admin/arguments/+page.server.ts` — `unpublish` action now captures `res`, checks `res.ok`, and only redirects on success; verified in commit `ac77a8f5f` and by direct file read |
| Public read paths (`get_cases`, `get_argument_with_utterances`, `get_argument_speakers`) | `status == PUBLISHED` | Defect-2 fix (48-10) | WIRED | All three functions read in full: each gates on BOTH `published_at IS NOT NULL` (preserved verbatim) AND `status == PUBLISHED` (added); `test_phase48_unpublish_visibility.py` ran directly and passed |
| `TrustGateBlocked` | router 422 mapping | `api/routers/admin.py` | WIRED | Confirmed via `48-REVIEW.md`'s IN-01 finding (non-blocking: router hardcodes the same string rather than reading `exc.code` — cosmetic, not a wiring break) and by reading the two-gate publish flow directly |

### Behavioral Spot-Checks / Direct Test Execution

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite | `./.venv/bin/python -m pytest -q` (run once, in full) | `1217 passed, 5 xfailed, 0 failed` in 163.41s | PASS — matches the phase's own claimed baseline exactly |
| Trust domain unit tests | `pytest api/tests/test_trust_domain.py` | 44 collected as part of full run; isolated run confirmed passing | PASS |
| Trust recompute tests | `pytest api/tests/test_trust_recompute.py` | 18 passed | PASS |
| Delete-cascade regression | `pytest api/tests/test_admin_arguments_service.py -k "cascade or delete_argument"` | 11 passed | PASS |
| Unpublish public-visibility regression | `pytest api/tests/test_phase48_unpublish_visibility.py` | 1 passed | PASS |
| Publish gate (two-gate ordering, override) | `pytest api/tests/test_published_gate.py` | 31 passed (part of combined 132-test run) | PASS |
| Public leak ban | `pytest api/tests/test_trust_public_leak_ban.py` | 11 passed (part of combined 132-test run) | PASS |
| List-page UI contract (incl. CR-01 regression) | `pytest api/tests/test_phase48_list_publish_override_ui_contract.py` | passed (part of combined 132-test run) | PASS |
| Detail-page UI contract + error rendering | `pytest api/tests/test_phase48_publish_override_ui_contract.py test_phase48_detail_publish_error_rendering_contract.py` | 22 passed | PASS |
| Migration state | `./.venv/bin/python -m alembic current` | `0027 (head)` | PASS |
| Frontend type/lint check | `npm run check` (app/) | `806 FILES 0 ERRORS 36 WARNINGS` | PASS — matches claimed baseline |
| Debt-marker scan | grep TBD/FIXME/XXX/TODO/HACK/placeholder across all phase-48-touched files | no hits | PASS |
| Production PIPELINE-vocabulary completeness | grep `ArgumentStatusEnum.PIPELINE` outside tests/enum/comments | no hits | PASS |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|---|---|---|---|---|
| TRUST-01 | 48-01, 48-03, 48-06 | trust_tier derived by one documented function | SATISFIED | `derive_tier`, leak-ban tests, direct code read |
| TRUST-02 | 48-01, 48-04, 48-05, 48-06 | floor rollup, materialized, recomputed on every mutation | SATISFIED | `floor_tier`, `recompute_argument_tier` call-site trace |
| TRUST-03 | 48-02, 48-04, 48-05 | born candidate, tier set on arrival | SATISFIED | model default + explicit corpus kwarg + PDF no-kwarg reliance, both verified directly |
| TRUST-04 | 48-07, 48-08, 48-10 | single published_at gate, hard-blocked on UNCERTAIN | SATISFIED | two-gate ordering read directly in `publish_argument` |
| TRUST-05 | 48-07, 48-08, 48-10 | logged, deliberate, per-argument, non-sticky override | SATISFIED | override columns, `.strip()` server-side check, no persistent flag (grepped) |

No orphaned requirements: all five TRUST-0X IDs are claimed by at least one plan's
frontmatter, and REQUIREMENTS.md marks all five `Complete` mapped to Phase 48 — consistent
with what the code demonstrates independent of that document's own claim.

### Anti-Patterns Found

None in phase-48-touched files (checked `api/domain/trust.py`, `api/services/trust.py`,
`api/services/admin_arguments.py`, `api/services/admin_jobs.py`, the migration, both admin
arguments frontend route pairs, the pipeline commands, and `scripts/delete_fixture_argument.py`
for TBD/FIXME/XXX/TODO/HACK/placeholder/stub-return patterns — zero hits).

### Known, Accepted, Deliberately Deferred (confirmed present, not counted as gaps)

Per the verification brief, the following were checked for presence/recording only, not
treated as failures of this phase:

- `reset_to_fixture`'s shared-transaction stale-`created_at` issue (Finding 2's storage
  half) — confirmed open in `WINDOWS.md` #9, `48-EVIDENCE.md` §5/§7, with the display-order
  half genuinely fixed (`get_argument_detail` now orders by `ArgumentStatusLog.id.asc()` —
  confirmed by direct grep) and regression-tested.
- Detail-page unpublish-error rendering verified by static contract test only — confirmed
  recorded as such in `48-10-SUMMARY.md` and `48-EVIDENCE.md` §7, not silently upgraded.
- Fixtures 15169/22372 reading `uncertain` instead of `trusted` — confirmed as `WINDOWS.md`
  #10 and `48-EVIDENCE.md` Finding 1, correctly attributed to a real ConvoKit
  unattributed-speaker sentinel rather than a `derive_tier` defect (independently verified:
  the derivation code correctly implements D-11's "NULL person_id floors to UNCERTAIN" rule
  regardless of why the row is NULL).
- Participant editability scoped to CANDIDATE-only, widening deferred to Phase 49 — confirmed
  present as an open item in `48-EVIDENCE.md` §7, not implemented in this phase's code (as
  expected — it is explicitly out of scope per `48-CONTEXT.md`).
- `admin_jobs.py`'s `list_jobs`/`get_run_id_for_step` `created_at`-first ordering — confirmed
  left unchanged, recorded as a follow-up candidate in `48-EVIDENCE.md` §5 Finding 2.
- `WINDOWS.md` entries #1 (phase 39), #2 (phase 44), #5 (phase 47) — confirmed still `open`
  and predate this phase; #7, #8 confirmed `fixed`.

### Code Review Follow-Through

`48-REVIEW.md` (run after plan close-out) found 1 critical + 2 warnings + 2 info items.
Independently confirmed:
- CR-01 (list-page `unpublish` swallowing failure) — fixed in `ac77a8f5f`, verified by
  direct file read: `res` is now captured, `res.ok` checked, redirect only on success.
- CR-02 (stale docstring) — fixed in `39a8fdcba`.
- CR-03 (missing submitting/disabled state on Unpublish button) — fixed alongside CR-01.
- IN-01/IN-02 — left open by design (info-severity, explicitly not required this round);
  confirmed genuinely cosmetic (a router hardcoding a literal that happens to match a class
  attribute; a string-tagged exception-dispatch pattern) and do not affect gate correctness.

## Gaps Summary

None found. Every phase-goal-level truth (materialized trust_tier rollup, candidate-on-arrival,
single published_at gate hard-blocked on UNCERTAIN, logged non-sticky operator override) was
independently re-derived from the codebase — not accepted from SUMMARY.md or EVIDENCE.md
narrative — and confirmed by direct code reads plus live test execution in this session,
including a from-scratch full-suite run (1217 passed / 5 xfailed / 0 failed, matching the
phase's own claimed number) and an `npm run check` run (0 errors, matching the claimed
number). The one blocker the phase's own code review found post-close-out (list-page
unpublish silently swallowing failures) is confirmed fixed and regression-tested. The
apolitical hard constraint (trust_tier never on any public response) was independently
re-verified by grepping every public schema, router, and service module directly, not by
trusting the existing test's green status alone. The two-gate publish ordering was read in
full and confirmed correct: `override_reason` is never consulted before the non-overridable
`resolved_at` gate. Every recompute call site across both the API service layer and the
offline pipeline was traced and confirmed to precede its writer's own commit.

No must-have required human/browser verification beyond what the phase's own operator
sign-off (`48-EVIDENCE.md` §8) already recorded, and that sign-off's claims (candidates
hidden from the admin list, Status History ordering, public visibility of the Published
fixture, zero-drift recompute) were each independently re-confirmed against the code paths
that produce them, not merely re-read from the sign-off text.

---

_Verified: 2026-08-21T15:14:12Z_
_Verifier: Claude (gsd-verifier)_
