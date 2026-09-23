---
phase: 49-review-model
plan: 04
subsystem: review-model
tags: [authority-ladder, provenance, trust-tier, fastapi, sqlalchemy, postgresql]

requires:
  - phase: 49-review-model plan 01
    provides: "review_state PG enum (4 permanent values) + argument_participants.review_state/source/method columns; the value_discrepancy table (schema only, unpopulated); _load_constituents feeding derive_tier real per-participant values"
  - phase: 49-review-model plan 02
    provides: "people.review_state/.provenance_metadata replacing the legacy Phase 38 fields outright — the review_state vocabulary this plan's authority ladder reads for Person is in its final, post-fold shape"

provides:
  - "api/domain/authority.py — the pure write-acceptance authority ladder: AuthorityRank, WriteDecision, authority_rank(), decide_write() (D-31/D-31b), exhaustively matrix-tested"
  - "api/services/admin_review.py — the ONE authority-gated writer for argument_participants and people: apply_participant_value_change, apply_person_value_change, record_value_discrepancy, close_open_discrepancies (D-31/D-31a)"
  - "update_participant_side, update_resolve_row_for_job, and update_person all delegate their value writes through the gate — no second, ungated write path survives to those columns"
  - "update_resolve_row_for_job's participant editability widened from CANDIDATE-only to every unpublished lifecycle state (candidate/draft/unpublished); list_resolve_rows_for_job's editable flag matches"
  - "D-17: an ArgumentParticipant with person_id IS NULL and review_state=operator_confirmed (via confirm_unattributable) contributes VERIFIED instead of UNCERTAIN to the argument's trust floor; an ordinary confirm never reaches this path"
  - "resolve_participant_review's full 3-action set (confirm, confirm_unattributable, reflag) with distinct tagged-ValueError guards; resolve_person_review mirrors it minus confirm_unattributable and the recompute call (48 D-10 no-fan-out)"
  - "list_review_queue_arguments now attaches each constituent's open discrepancies (id ASC); new list_review_queue_people; GET /api/admin/review/people and PATCH /api/admin/review/people/{person_id}"
  - "D-34: the public-leak-ban test's BANNED_KEYS widened from 1 to 7 keys (trust_tier, review_state, source, method, incoming_value, existing_value, resolved_at), iterated per reachable public model, plus an AST import ban on api.domain.authority/api.schemas.admin_review from public schemas"
  - "Fixes the pre-existing, previously out-of-scope test_admin_jobs_service.py regression (WINDOWS.md #11, now fixed): resolve_job and update_resolve_row_for_job backfill ArgumentParticipant.source/.method from the job's own parse-step ImportRun when never stamped"

affects: [49-05-review-ui, 49-06]

actuals:
  tokens: 57000
  tasks: 3
  commits: 6

tech-stack:
  added: []
  patterns:
    - "Authority ladder as a separate pure module from trust.py's derive_tier — same rank-ordering int-enum shape, answers a DIFFERENT question (may this write happen vs. how much do we trust this row), never collapsed into one function"
    - "Provenance backfill (source/method) via a conditional CASE expression inside an already-necessary bulk UPDATE, or via ORM attribute assignment on an already-loaded object — both avoid adding a second literal update(Table) call site, keeping a single, auditable write path per table per function"
    - "A 'best-effort' autouse test-cleanup fixture must gate on the resolved real database name (mirroring pipeline/tests/conftest.py::_reset_test_db's scotus_test check) and catch DBAPIError around its own query — _db_configured() alone accepts synthetic/unreachable probe URLs, and a bare query can break a test's deliberate mid-test schema downgrade"

key-files:
  created:
    - api/domain/authority.py
    - api/tests/test_authority_matrix.py
  modified:
    - api/services/admin_review.py
    - api/services/admin_arguments.py
    - api/services/admin_jobs.py
    - api/services/admin_people.py
    - api/services/trust.py
    - api/schemas/admin_review.py
    - api/routers/admin_review.py
    - api/tests/test_admin_review_service.py
    - api/tests/test_trust_public_leak_ban.py
    - api/tests/test_admin_jobs_service.py
    - api/tests/test_admin_jobs_phase25.py
    - api/tests/test_admin_people_phase25.py
    - api/tests/conftest.py

key-decisions:
  - "The D-18 provenance gap the must_clear_regression flagged (resolve_job/update_resolve_row_for_job never stamping source/method) is fixed by backfilling from the job's own parse-step ImportRun (source=corpus/method=direct in the failing tests' fixtures), NOT by routing the incoming write's authority as operator/manual as the environment note's prose literally suggested. Verified by tracing derive_tier's actual rule table: operator/manual authority only ever produces VERIFIED (rule 3), never TRUSTED, and both regression tests assert TrustTier.TRUSTED. Only rule 4 ((source,method) in {(corpus,direct),(seed,direct)}) reaches TRUSTED, so the row's stored source/method — not the incoming write's authority — had to become corpus/direct. This is a genuine backfill of missing provenance metadata (D-20's mapping table has no row for this admin-assisted resolve mechanism), not an authority-gate decision, and is written via a conditional CASE / ORM attribute assignment rather than a second literal update(ArgumentParticipant) call."
  - "apply_participant_value_change/apply_person_value_change's incoming_review_state parameter is always passed as the empty string by callers in this plan (never operator_confirmed/operator_edited) — safe because incoming_source='operator' already reaches AuthorityRank.OPERATOR via authority_rank's rule 2, independent of the literal review_state string passed."
  - "update_person's four name-part writes re-derive full_name from the ACTUAL per-field post-gate outcome (accepted vs rejected), not from the caller's raw prepared values — otherwise a rare re-edit hitting REJECT_AND_RECORD on one field while another field's ACCEPT_AND_RECORD succeeds would leave full_name inconsistent with the individually-persisted structured columns."
  - "close_open_discrepancies is called unconditionally by update_participant_side/update_person/resolve_participant_review/resolve_person_review on every invocation, even when the SAME call's own gate write was REJECT_AND_RECORD (creating a discrepancy that gets closed in the same transaction it was opened in). Implemented exactly as the plan's action text specifies; not second-guessed, since the alternative (skip closing when the gate rejected) is not what the plan asked for and this plan's mandate does not include revisiting that specific interaction."
  - "The autouse value_discrepancy orphan-sweep fixture added to api/tests/conftest.py during this plan's own verification was found to break two unrelated hermetic tests on first pass (a deliberately-unreachable synthetic-DB isolation probe, and a test that deliberately downgrades the schema below migration 0028) — fixed by gating on the resolved database name being exactly 'scotus_test' and wrapping the sweep query in a DBAPIError catch, both self-caught and fixed before this plan's own commit, not left for a future plan."

patterns-established:
  - "A ledger table with no real FK to its target row (value_discrepancy.target_id, by design — must outlive a deleted/merged target) needs an explicit sweep in shared test teardown machinery, or it silently accumulates across every pytest run against the shared scotus_test database."

requirements-completed: []

coverage:
  - id: D1
    description: "api/domain/authority.py: the pure write-acceptance authority ladder (AuthorityRank, WriteDecision, authority_rank, decide_write) with a fail-closed UNKNOWN rung and an equal-authority-rejects boundary, exhaustively matrix-tested (50 rank x rank x differs cases + a count guard + named behavior tests)"
    requirement: "REVIEW-02"
    verification:
      - kind: unit
        ref: "api/tests/test_authority_matrix.py#test_decide_write_matrix (50 parametrized cases)"
        status: pass
      - kind: unit
        ref: "api/tests/test_authority_matrix.py#test_matrix_exercises_every_combination"
        status: pass
      - kind: unit
        ref: "api/tests/test_authority_matrix.py#test_equal_authority_with_differing_values_rejects_and_records"
        status: pass
      - kind: other
        ref: "grep -Ev '^\\s*#' api/domain/authority.py | grep -Ec 'import (fastapi|sqlalchemy|alembic)' -> 0"
        status: pass
    human_judgment: false
  - id: D2
    description: "The ONE authority-gated writer (apply_participant_value_change/apply_person_value_change/record_value_discrepancy/close_open_discrepancies) — update_participant_side, update_resolve_row_for_job, and update_person all delegate their value writes through it; no second, ungated write path to those columns survives"
    requirement: "REVIEW-02"
    verification:
      - kind: integration
        ref: "api/tests/test_authority_matrix.py#test_equal_value_updates_row_and_creates_no_discrepancy"
        status: pass
      - kind: integration
        ref: "api/tests/test_authority_matrix.py#test_equal_authority_differing_value_leaves_column_untouched_and_records_one_discrepancy"
        status: pass
      - kind: integration
        ref: "api/tests/test_authority_matrix.py#test_strictly_higher_authority_differing_value_updates_and_records_overwritten_value"
        status: pass
      - kind: integration
        ref: "api/tests/test_authority_matrix.py#test_manual_check_corpus_write_against_operator_edited_participant_rejects_and_records"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_arguments_service.py#test_update_participant_side_persists_descriptor_for_advocate"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_people.py#test_update_person_authoritative_name_edit_sets_operator_edited"
        status: pass
    human_judgment: false
  - id: D3
    description: "Participant editability widened from CANDIDATE-only to every unpublished lifecycle state (candidate/draft/unpublished); only PUBLISHED is read-only, matching both update_resolve_row_for_job's guard and list_resolve_rows_for_job's editable flag (folded todo 2026-08-21)"
    requirement: "REVIEW-02"
    verification:
      - kind: integration
        ref: "api/tests/test_authority_matrix.py#test_update_resolve_row_for_job_succeeds_on_draft_and_unpublished_but_not_published"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_jobs_service.py#test_update_resolve_row_accepts_candidate_draft_and_rejects_published"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_people_phase25.py#test_list_resolve_rows_editable_true_when_argument_draft"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_people_phase25.py#test_list_resolve_rows_editable_false_when_argument_published"
        status: pass
    human_judgment: true
    rationale: "The frontend readonlyMode flag at app/src/routes/admin/pipeline/[job_id]/+page.server.ts:294 still keys on status !== 'candidate' and was deliberately NOT widened here — it gates BOTH the Resolve card and the unrelated ArgumentDetailsCard metadata-edit form behind one shared flag, and widening it wholesale would silently expand this plan's scope into a different, untested feature. Backend/API editability is fully fixed and tested; the frontend flag split (or a scoped widen) is left for 49-05 (review UI) or a dedicated follow-up. A human should confirm this is an acceptable interim state before UAT sign-off."
  - id: D4
    description: "Fixes the pre-existing test_admin_jobs_service.py regression (WINDOWS.md #11, now marked fixed): resolve_job and update_resolve_row_for_job backfill ArgumentParticipant.source/.method from the job's parse-step ImportRun when never stamped, so a freshly-resolved corpus participant reads TRUSTED instead of floor-UNCERTAIN"
    requirement: "REVIEW-02"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_jobs_service.py#test_resolve_job_recomputes_tier_when_last_speaker_resolves"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_jobs_service.py#test_repeated_writer_call_leaves_tier_unchanged"
        status: pass
    human_judgment: false
  - id: D5
    description: "D-17: confirm_unattributable on a person_id-IS-NULL participant lifts the trust floor to VERIFIED; an ordinary confirm on the same row is rejected with a distinct tagged error and never lifts the floor as a side effect; reflag is the only backward transition (never to unreviewed); a resolve action closes multiple open discrepancies with one shared resolved_at"
    requirement: "REVIEW-04"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_review_service.py#test_confirm_unattributable_lifts_uncertain_floor"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_review_service.py#test_confirm_on_unresolved_participant_rejected_with_distinct_error"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_review_service.py#test_confirm_unattributable_on_resolved_participant_rejected"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_review_service.py#test_reflag_sets_needs_review_on_operator_confirmed_row"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_review_service.py#test_reflag_rejected_on_never_reviewed_row"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_review_service.py#test_multiple_open_discrepancies_close_with_identical_resolved_at"
        status: pass
    human_judgment: false
  - id: D6
    description: "D-34: the public-leak ban covers trust_tier, review_state, source, method, incoming_value, existing_value, and resolved_at across the full public model graph (7x case growth), an AST scan additionally bans importing api.domain.authority/api.schemas.admin_review from public schemas, and the false-green guard is extended to prove ReviewQueueConstituent (admin-only) DOES carry review_state"
    requirement: "REVIEW-02"
    verification:
      - kind: integration
        ref: "api/tests/test_trust_public_leak_ban.py#test_public_response_model_never_declares_trust_tier (56 parametrized cases)"
        status: pass
      - kind: unit
        ref: "api/tests/test_trust_public_leak_ban.py#test_admin_detail_contract_does_declare_trust_tier"
        status: pass
      - kind: unit
        ref: "api/tests/test_trust_public_leak_ban.py#test_public_schema_modules_never_import_trust_tier"
        status: pass
      - kind: other
        ref: "Manual spot-check: temporarily added review_state: str to PersonResponse, confirmed test_public_response_model_never_declares_trust_tier[PersonResponse-review_state] fails naming PersonResponse, reverted, confirmed clean git diff"
        status: pass
    human_judgment: false

duration: 100min
completed: 2026-08-23
status: complete
---

# Phase 49 Plan 04: Authority Ladder Summary

**A pure, exhaustively-matrix-tested authority ladder (`api/domain/authority.py`) gates every write to `argument_participants`/`people` through one function in `api/services/admin_review.py`; three existing writers (`update_participant_side`, `update_resolve_row_for_job`, `update_person`) now delegate to it instead of writing directly, participant editability widens to every unpublished state, D-17's unattributable-floor lift and the full confirm/confirm_unattributable/reflag action set land, D-34 widens the public-leak ban to seven keys, and the phase's two pre-existing `test_admin_jobs_service.py` regressions (deferred since plan 49-02) are fixed by backfilling missing participant provenance from the job's own parse-step `ImportRun`.**

## Performance

- **Duration:** ~100 min
- **Tasks:** 3
- **Files touched:** 15 (2 created, 13 modified)
- **Commits:** 6

## Accomplishments

- **`api/domain/authority.py`** — `AuthorityRank` (UNKNOWN < PDF_LLM < PDF_RULE_BASED < CORPUS < OPERATOR), `WriteDecision` (ACCEPT / ACCEPT_AND_RECORD / REJECT_AND_RECORD), `authority_rank()` (review_state checked first per D-22, then source, then pdf_pipeline method), and `decide_write()` (equal authority rejects — the phase's stated "single most important boundary"). 60 pure unit tests (50-case exhaustive matrix + a count guard + 9 named tests), zero FastAPI/SQLAlchemy/Alembic imports.
- **The ONE authority gate**, added to `api/services/admin_review.py`: `apply_participant_value_change`, `apply_person_value_change` (both never commit), `record_value_discrepancy`, `close_open_discrepancies` (one UPDATE, one shared `resolved_at`, so close order is unobservable). `_values_differ` is the single named home of the REVIEW-01/encoding normalization contract (name-parts via `normalize_name_part`, everything else via strip+blank-to-None, plain `==`).
- **All three named writers now delegate**: `update_participant_side` and `update_person` gate their fields then stamp `review_state=OPERATOR_EDITED` (never touching `source`/`method`, per D-22) and close open discrepancies; `update_resolve_row_for_job` gates `side`/`descriptor` and its status guard widened from CANDIDATE-only to "anything but PUBLISHED" (the folded 2026-08-21 todo) — `list_resolve_rows_for_job`'s `editable` flag was updated to match.
- **D-18 regression fixed** (the two `test_admin_jobs_service.py` failures the orchestrator flagged, deferred since plan 49-02/WINDOWS.md #11): `resolve_job` and `update_resolve_row_for_job` now backfill `ArgumentParticipant.source`/`.method` from the job's own "parse" step `ImportRun` whenever the row was never stamped — via a conditional `CASE` inside the existing bulk UPDATE (resolve_job) or ORM attribute assignment on the already-loaded object (update_resolve_row_for_job), so neither adds a second literal write path. **The fix is NOT what the environment note's prose described** (routing the incoming write as `operator`/`manual` authority, which only ever reaches `derive_tier` rule 3 → VERIFIED) — both failing tests assert `TrustTier.TRUSTED`, reachable only via rule 4 (`(source,method) in {(corpus,direct),(seed,direct)}`), confirming the row's own provenance columns, not the write's authority, had to change. See Deviations.
- **D-17's floor lift**: `_load_constituents`'s NULL-`person_id` branch now checks `review_state == operator_confirmed` before flooring to UNCERTAIN — `confirm_unattributable` sets exactly that state, lifting the floor to VERIFIED; an ordinary `confirm` is rejected before it ever reaches this branch, so it can never trigger the lift as a side effect.
- **Full resolve-action set**: `resolve_participant_review` dispatches `confirm` / `confirm_unattributable` / `reflag` with distinct tagged `ValueError`s (`unresolved_requires_unattributable`, `participant_is_resolved`, `row_not_yet_reviewed`), mapped to 422 by the router. `resolve_person_review` mirrors it minus `confirm_unattributable` (D-17 is participant-only) and minus the recompute call (48 D-10's no-fan-out rule). No action ever writes `unreviewed` (D-25) — verified by inspection (no `.values(review_state=ReviewState.UNREVIEWED)` write pattern anywhere in the dispatch) rather than the literal blunt grep the plan's acceptance criteria specified (see Deviations).
- **`list_review_queue_arguments`** now attaches each constituent's open discrepancies (ordered `id` ASC); new **`list_review_queue_people`** (D-02); new routes `GET /api/admin/review/people` and `PATCH /api/admin/review/people/{person_id}`.
- **D-34**: `test_trust_public_leak_ban.py`'s `BANNED_KEY` → `BANNED_KEYS` (7 keys), parametrized per reachable public model (56 cases, up from 8 — exactly 7x); the AST import scan now also bans `api.domain.authority`/`api.schemas.admin_review` on public schema modules; the false-green guard now also proves `ReviewQueueConstituent` (admin-only) DOES carry `review_state`. Manually verified: a temporary `review_state` field added to `PersonResponse` fails the ban naming that model; reverted clean.
- **Test-hygiene fix discovered by this plan's own verification, not deferred**: the new gate records `value_discrepancy` rows as a side effect of several pre-existing tests exercising `update_participant_side`/`update_resolve_row_for_job` repeatedly; that table has no real FK to its target row (by design), so those rows leaked past existing teardowns. Added an autouse sweep fixture to `api/tests/conftest.py` (scoped to the real `scotus_test` database, wrapped in a `DBAPIError` catch) plus explicit cleanup in the specific teardown helpers this plan's tests use directly.

## Task Commits

1. **Task 1 — pure authority ladder + exhaustive matrix:** `9cea6bcbf` (feat)
2. **Task 2 — the gate, delegation, and the D-18 provenance fix:** `14fe8be37` (feat) — includes some Task 3 `admin_review.py` additions (resolve-action dispatch, `list_review_queue_people`, discrepancy attachment) that were staged together with Task 2's gate work before the Task 2 commit landed; see Deviations.
3. **Task 3 — resolve actions, D-17 floor lift, D-34 leak-ban extension:** `2ef9b6a4f` (feat)
4. **Follow-up — value_discrepancy teardown leak, found by this plan's own verification:** `a1eb45528` (fix), `cbc1f97d8` (fix), `4c98c2721` (fix)

## Files Created/Modified

- `api/domain/authority.py` — new, the pure authority ladder
- `api/tests/test_authority_matrix.py` — new, 67 tests (60 pure unit + 7 DB-gated integration)
- `api/services/admin_review.py` — the gate + discrepancy pair + full resolve-action dispatch + `list_review_queue_people` + discrepancy attachment on `list_review_queue_arguments`
- `api/services/admin_arguments.py` — `update_participant_side` delegates through the gate
- `api/services/admin_jobs.py` — `update_resolve_row_for_job` delegates + widened status guard; `resolve_job` backfills provenance
- `api/services/admin_people.py` — `update_person` delegates through the gate; `list_resolve_rows_for_job`'s `editable` flag widened to match
- `api/services/trust.py` — D-17 qualification on `_load_constituents`'s NULL-`person_id` branch
- `api/schemas/admin_review.py` — `ReviewActionRequest` widened to 3 actions; new `DiscrepancyDetail`, `ReviewQueuePersonItem`, `ReviewQueueStats`
- `api/routers/admin_review.py` — `GET /people`, `PATCH /people/{person_id}`
- `api/tests/test_admin_review_service.py` — 6 new named behavior tests
- `api/tests/test_trust_public_leak_ban.py` — D-34 extension
- `api/tests/test_admin_jobs_service.py`, `test_admin_jobs_phase25.py`, `test_admin_people_phase25.py` — 3 pre-existing tests updated for the widened editability rule; value_discrepancy teardown cleanup
- `api/tests/conftest.py` — new autouse `value_discrepancy` orphan-sweep fixture

## Decisions Made

See `key-decisions` in frontmatter above.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug, the must_clear_regression's prescribed fix was wrong] `update_resolve_row_for_job`/`resolve_job` provenance backfill uses corpus/direct from the parse ImportRun, not operator/manual authority routing**
- **Found during:** Task 2, before writing any code — traced `derive_tier`'s actual rule table against both failing tests' `TrustTier.TRUSTED` assertions
- **Issue:** The environment note's prescribed fix ("route through the authority-gated writer with incoming_source='operator', incoming_method='manual', which lands on derive_tier rule 3") is internally inconsistent with the tests it's meant to fix: rule 3 (`operator`/`manual` → VERIFIED) can never produce `TrustTier.TRUSTED`; only rule 4 (`(corpus,direct)`/`(seed,direct)` → TRUSTED) can. The tests' own fixtures create the underlying `ImportRun` with `source=CORPUS, method=DIRECT` — a strong signal the row's stored provenance, not the write's authority, needed to change.
- **Fix:** Implemented as described in the "Accomplishments" section — backfill from the job's parse-step `ImportRun` only when `source IS NULL`, never clobbering an existing stamp.
- **Files modified:** `api/services/admin_jobs.py`
- **Verification:** Both named regression tests pass with `TrustTier.TRUSTED`; `api/tests/test_admin_jobs_service.py` full module 12/12 passed.
- **Committed in:** `14fe8be37`

**2. [Rule 2 - Missing Critical] `list_resolve_rows_for_job`'s `editable` flag widened to match the write-side guard**
- **Found during:** Task 2, immediately after widening `update_resolve_row_for_job`'s status guard
- **Issue:** The Resolve card's read-side `editable` flag (`api/services/admin_people.py`) still keyed on `status == CANDIDATE`; leaving it unchanged would have shown the card as read-only in the UI for DRAFT/UNPUBLISHED arguments even though the backend now accepts the write — a direct, load-bearing inconsistency with what this task widened.
- **Fix:** `editable = argument.status != ArgumentStatusEnum.PUBLISHED`, matching the widened write guard exactly.
- **Files modified:** `api/services/admin_people.py`, `api/tests/test_admin_people_phase25.py` (updated one existing test, added one companion test)
- **Verification:** `test_list_resolve_rows_editable_false_when_argument_published`, `test_list_resolve_rows_editable_true_when_argument_draft` pass.
- **Committed in:** `14fe8be37`

**3. [Rule 3 - Blocking, pre-existing tests asserted the superseded rule] Three existing tests updated for the widened editability rule**
- **Found during:** Task 2's own full-suite verification gate
- **Issue:** `test_admin_jobs_phase25.py::test_update_resolve_row_for_job_does_not_reuse_advocate_side_endpoint` (source-contract assertion expecting the literal `ArgumentStatusEnum.CANDIDATE` guard text, and `synchronize_session=False` in a function body that no longer contains a direct `update()` call), `test_admin_jobs_phase25.py::test_update_resolve_row_rejects_edit_when_argument_not_pipeline`, and `test_admin_people_phase25.py::test_list_resolve_rows_editable_false_when_argument_not_pipeline` all asserted the pre-49-04 CANDIDATE-only rule this task deliberately supersedes.
- **Fix:** Rewrote each to assert against PUBLISHED (the new read-only boundary) instead of DRAFT/non-CANDIDATE, and updated the source-contract test to check for `ArgumentStatusEnum.PUBLISHED` + gate delegation (`apply_participant_value_change(`) + absence of a direct `update(ArgumentParticipant)` call, rather than the now-obsolete literal text.
- **Files modified:** `api/tests/test_admin_jobs_phase25.py`, `api/tests/test_admin_people_phase25.py`
- **Verification:** All three renamed/rewritten tests pass; full suite green.
- **Committed in:** `14fe8be37`

**4. [Rule 1 - Bug, found by this plan's own verification] `value_discrepancy` rows leaking past existing test teardowns**
- **Found during:** Post-Task-3 full-suite verification — a manual DB row-count check after a clean run showed orphaned rows
- **Issue:** `value_discrepancy.target_id` has no real FK to `argument_participants.id`/`people.id` (by design, so a discrepancy can outlive a deleted/merged target). Several tests this plan's gate now touches (both new and pre-existing, e.g. `test_update_participant_side_persists_descriptor_for_advocate`) seed a participant, exercise the gate, then delete the participant row directly — the discrepancy row it created has nothing catching it and silently accumulates in the shared `scotus_test` database across pytest runs.
- **Fix:** Added explicit `value_discrepancy` cleanup to the specific teardown helpers this plan's own tests use directly (`_teardown_rows` in `test_admin_jobs_service.py`, `_teardown_needs_review_participant` in `test_admin_review_service.py`, the inline teardown in `test_authority_matrix.py`'s status-guard test), plus a general autouse sweep fixture in `api/tests/conftest.py` that catches ANY orphan (target row no longer exists) after every `api/tests` test — covering pre-existing tests this plan didn't directly touch (e.g. `test_admin_arguments_service.py`) without needing to hunt down every call site.
- **Files modified:** `api/tests/test_admin_jobs_service.py`, `api/tests/test_admin_review_service.py`, `api/tests/test_authority_matrix.py`, `api/tests/conftest.py`
- **Verification:** A full clean suite run followed by a direct row-count check confirmed 0 `value_discrepancy` rows remaining.
- **Committed in:** `a1eb45528`, `cbc1f97d8`

**5. [Rule 1 - Bug, self-caught during the same verification pass] The orphan-sweep fixture itself initially broke two unrelated hermetic tests**
- **Found during:** Immediately after committing the fix in item 4 — the next full-suite run surfaced 3 new failures + 7 new errors that were not present before
- **Issue:** The autouse sweep's guard (`_db_configured()` alone) accepts `tests/test_pytest_isolation_invocation_shapes.py`'s deliberately-unreachable synthetic probe URL (`postgresql+asyncpg://probe:probe@127.0.0.1:1/...`), so the sweep's own query raised `ConnectionRefusedError` from fixture teardown, failing that isolation probe for a reason unrelated to what it tests. Separately, `test_migration_0022_person_name_authority.py` deliberately downgrades the schema mid-test past migration 0028 (before `value_discrepancy` exists), and the sweep's unguarded query raised `UndefinedTableError` there too.
- **Fix:** Added the same "resolved database name must be exactly `scotus_test`" guard `pipeline/tests/conftest.py::_reset_test_db` already uses (checked via `sqlalchemy.engine.make_url`), plus a `DBAPIError` catch around the sweep's own query, so this best-effort cleanup can never fail an unrelated test regardless of schema state.
- **Files modified:** `api/tests/conftest.py`
- **Verification:** `tests/test_pytest_isolation_invocation_shapes.py` (3/3) and `api/tests/test_migration_0022_person_name_authority.py` (10/10) both pass again; a subsequent full clean suite run (1376 passed, 5 xfailed, 0 failed) confirmed no other regressions, and a direct row-count check confirmed the sweep still works for its intended targets.
- **Committed in:** `4c98c2721`

### Documented, Not Fixed (Rule 4 — flagged, deliberately not widened)

**6. Frontend `readonlyMode` flag NOT widened to match the backend's widened editability rule**
- **Found during:** Task 2, while widening the backend guard and its two backend read-side flags
- **Issue:** `app/src/routes/admin/pipeline/[job_id]/+page.server.ts:294` still computes `readonlyMode = argument.status !== 'candidate'`, now inconsistent with the backend. But `readonlyMode` gates BOTH the Resolve card (this task's concern) AND the unrelated `ArgumentDetailsCard` metadata-edit form (`?/saveJobMetadata` — case name, docket, argued date, question number) — a single flag serving two different editability concerns. Widening it wholesale would silently make argument-metadata editing available in DRAFT/UNPUBLISHED too, a feature this plan never touched, tested, or was asked to widen; splitting the flag into two is a small architectural change outside this task's explicit scope (`api/services/admin_review.py`, `admin_arguments.py`, `admin_jobs.py`, `admin_people.py` — no frontend files).
- **Not fixed.** Left for plan 49-05 (review UI, which owns this file's directory scope) or a dedicated follow-up. Recorded here so it isn't silently lost.
- **Impact on plan:** No backend behavior depends on this; it is purely a frontend consistency gap. Coverage item D3 above marks this `human_judgment: true` for exactly this reason.

**7. Acceptance criteria's blunt grep checks not fully satisfiable as literally worded (documented, not silently skipped)**
- `grep -c 'update(ArgumentParticipant)' api/services/admin_jobs.py` equals 0 — literally: 2 occurrences remain, both OUTSIDE this task's scope (`resolve_job`'s pre-existing person_id-fill UPDATE at line ~535, and `create_person_for_job`'s pre-existing person_id+side UPDATE at line ~1080). Gating person_id resolution through the value-authority gate would be semantically wrong under the current `_values_differ`/`decide_write` design (a first-time NULL→value fill always registers as "differs" against an UNKNOWN-rank existing row, so every ordinary resolve action would manufacture a spurious `value_discrepancy` audit row) — a design question outside this task's mandate (must_haves names only `update_participant_side`/`update_resolve_row_for_job`/`update_person` as the three delegating writers). `update_resolve_row_for_job`'s own block has zero such occurrences (confirmed by the rewritten source-contract test in item 3 above).
- `grep -c 'update(ArgumentParticipant)' api/services/admin_arguments.py` equals 0 — one occurrence remains: the `review_state=OPERATOR_EDITED` write the plan's own action text explicitly directs as a DIRECT write (not through the gate), immediately after `update_participant_side`'s two gate calls. The gate's job is value-authority arbitration; `review_state` is the authority signal itself, not a gated value.
- `grep -c 'ReviewState.UNREVIEWED' api/services/admin_review.py` equals 0 — literally: 5 occurrences remain, but none is a write (`.values(review_state=ReviewState.UNREVIEWED)`); they are one filter-query condition (`list_review_queue_people`), two guard *comparisons* (rejecting `reflag` on an unreviewed row), and two explanatory comments. Confirmed via `grep -n 'values(review_state=ReviewState.UNREVIEWED'` returning no matches.
- **Not fixed** (these are textual-check-vs-actual-intent mismatches, not defects) — each verified correct by inspection and recorded here rather than silently claimed as literally satisfied.

---

**Total deviations:** 5 auto-fixed (2 bugs including the must_clear_regression's own prescribed-fix correction, 1 missing-critical consistency fix, 1 blocking pre-existing-test update, 1 self-caught test-infrastructure bug), 2 documented-not-fixed (1 deliberate scope boundary, 1 acceptance-criteria wording mismatch).
**Impact on plan:** All fixes were either directly required for correctness (the D-18 regression, the editability consistency, the pre-existing test updates) or necessary to keep this plan's OWN new test infrastructure from silently corrupting the shared test database or breaking unrelated hermetic tests. No scope creep into person_id resolution gating or the frontend readonlyMode flag — both are flagged, not silently expanded into or silently ignored.

## Issues Encountered

None beyond the deviations documented above. Multiple full-suite runs were needed to distinguish real regressions from test-database cross-talk caused by running scoped diagnostic scripts concurrently with a background full-suite run during the value_discrepancy leak investigation — resolved by re-running the full suite in isolation (nothing else touching the DB) for the final, trustworthy result.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- REVIEW-02 and REVIEW-04 remain `Pending` in `.planning/REQUIREMENTS.md` — both are shared with sibling plans not yet complete (REVIEW-02 with 49-06; REVIEW-04 with 49-01 [complete], 49-05, 49-06) per the shared-ID gate (`requirements.ready-ids` returned `0/2 ready`). No action taken; correct per protocol.
- `.planning/WINDOWS.md` entry 11 (the two `test_admin_jobs_service.py` regressions) marked `fixed`.
- The folded todo `.planning/todos/pending/2026-08-21-widen-participant-editability-to-all-unpublished-states.md` is now backend-complete (API guard + both read-side flags widened) but NOT fully closed — the frontend `readonlyMode` split (item 6 above) remains. Left in `pending/`, not moved to `completed/`, since the request's frontend half is still open.
- Plan 49-05 (review UI) can now build the full queue screen (People tab, discrepancy display, the confirm/confirm_unattributable/reflag actions) against a real, tested backend — this plan intentionally shipped no frontend changes.
- `api/domain/trust.py` confirmed byte-identical throughout (`git diff --stat api/domain/trust.py` empty at every checkpoint).
- Full suite: **1376 passed, 5 xfailed, 0 failed** (baseline at plan start: 1252 passed / 2 failed [the D-18 regression, now fixed] / 5 xfailed). `python3 -m compileall -q pipeline api scripts tests alembic` clean. `npm --prefix app run check`: 0 errors, 37 warnings (unchanged from the 49-03 baseline — no frontend files touched).

## Self-Check: PASSED

- `api/domain/authority.py`, `api/tests/test_authority_matrix.py` confirmed present via `git show`.
- Commits `9cea6bcbf`, `14fe8be37`, `2ef9b6a4f`, `a1eb45528`, `cbc1f97d8`, `4c98c2721` all found in `git log --oneline`.
- `./.venv/bin/python -m pytest api/tests/test_authority_matrix.py -q` → 67 passed.
- `./.venv/bin/python -m pytest api/tests/test_admin_jobs_service.py -q` → 12 passed (both named regression tests pass with `TrustTier.TRUSTED`).
- `./.venv/bin/python -m pytest api/tests/test_admin_review_service.py -q` → 15 passed.
- `./.venv/bin/python -m pytest api/tests/test_trust_public_leak_ban.py -q` → 59 passed (56 parametrized ban cases, up from 8 pre-plan — exactly 7x).
- Full bare `./.venv/bin/python -m pytest -q` (run in isolation, nothing else touching the DB) → **1376 passed, 5 xfailed, 0 failed**.
- Direct row-count check on `value_discrepancy` after that clean run → 0 rows (no leak).
- `python3 -m compileall -q pipeline api scripts tests alembic` → clean.
- `npm --prefix app run check` → 0 errors, 37 warnings (same baseline as 49-03).
- `git diff --stat api/domain/trust.py` → empty.
- Manual leak-ban spot-check (temporary `review_state` field on `PersonResponse`, confirmed failure naming the model, reverted, confirmed clean diff) → PASSED.

---
*Phase: 49-review-model*
*Completed: 2026-08-23*
