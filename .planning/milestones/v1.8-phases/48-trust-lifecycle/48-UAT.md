---
status: complete
phase: 48-trust-lifecycle
source: 48-01-SUMMARY.md, 48-02-SUMMARY.md, 48-03-SUMMARY.md, 48-04-SUMMARY.md, 48-05-SUMMARY.md, 48-06-SUMMARY.md, 48-07-SUMMARY.md, 48-08-SUMMARY.md, 48-09-SUMMARY.md, 48-10-SUMMARY.md
started: 2026-08-21T15:40:38Z
updated: 2026-08-21T16:56:05Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running API/dev server. Clear ephemeral state (temp DBs, caches, lock files). Bring the stack up from scratch: `alembic upgrade head` applies migration 0027 (candidate enum value, arguments.trust_tier, argument_status_log override columns) cleanly on a fresh DB, the FastAPI app boots with no errors, and a primary read (/admin/arguments list or the public arguments endpoint) returns live data with trust_tier populated.
source_plan: injected (api/main.py + alembic/versions/0027_trust_tier_and_candidate_status.py modified)
result: pass

### 2. [48-01 D7] derive_tier rule 3 (operator+manual -> VERIFIED) is a flagged planner assumption not expli…
expected: derive_tier rule 3 (operator+manual -> VERIFIED) is a flagged planner assumption not explicitly stated in the source design note — needs operator confirmation.
rationale: The assumption's correctness depends on a policy call (whether an operator-authored, unreviewed row should be VERIFIED by construction) that the design note leaves ambiguous; automated tests can only prove the implementation is internally consistent and total, not that the policy choice is the one the operator intends. Flagged inline in api/domain/trust.py's module docstring and in 48-01-PLAN.md's <flagged_assumptions>.
coverage_reason: human_judgment
requirement: —
source_plan: 48-01
result: pass

### 3. [48-03 D3] The ban is proven to be a ban, not an absence: a companion assertion checks that the admin…
expected: The ban is proven to be a ban, not an absence: a companion assertion checks that the admin-only ArgumentDetail contract DOES declare trust_tier, so Test 1 cannot be passing vacuously because nothing anywhere declares the field.
rationale: This assertion is EXPECTED to fail until plan 48-07 lands trust_tier on ArgumentDetail (D-20) — both plans ship in the same phase, and this plan's own <acceptance_criteria> anticipates the failure by name. A human (or the phase-close verifier) must confirm this specific, named test is the sole failure and that it turns green once 48-07 closes, rather than the automated gate silently treating it as pass or fail on its own.
coverage_reason: human_judgment
requirement: TRUST-01
source_plan: 48-03
result: pass

### 4. [48-03 D4] A future public schema that adds any trust-derived field (not just the literal trust_tier …
expected: A future public schema that adds any trust-derived field (not just the literal trust_tier key) would be caught before release.
rationale: Flagged in 48-03-PLAN.md's <flagged_assumptions> as a backstop-only claim: the tests check one literal key name and one banned import name, not semantic intent. No automated evidence can prove a not-yet-invented field name would be caught; this abstains to human review by design, matching the plan's own documented abstention.
coverage_reason: human_judgment
requirement: —
source_plan: 48-03
result: pass

### 5. [48-07 D8] The blocked-publish payload's structure is rich enough for Phase 49's review queue to reus…
expected: The blocked-publish payload's structure is rich enough for Phase 49's review queue to reuse without re-deriving it.
rationale: Flagged in 48-07-PLAN.md's <flagged_assumptions> as a backstop-only claim — Phase 49's review queue does not exist yet, so no automated evidence can prove this phase's payload shape (code/trust_tier/blockers/message) will be reused as-is. Abstains to human review at Phase 49 planning time, per the plan's own documented abstention.
coverage_reason: human_judgment
requirement: —
source_plan: 48-07
result: pass

### 6. [48-08 D3] The non-overridable resolved_at gate (D-14) renders a message with NO override field offer…
expected: The non-overridable resolved_at gate (D-14) renders a message with NO override field offered, distinguishing it from the overridable trust gate.
rationale: Operator browser walkthrough step 8 was NOT executed — no argument whose resolve step never ran was available in the seeded fixture set. The D-14 must-have is satisfied in code and locked by the static contract test (D3's `other` entry), but the live-browser rendering of this exact branch is unverified. Tracked as WINDOWS.md entry #8 (kind=unrun-verify, status=open). Do not auto-pass this row from the `other` evidence alone — a human must confirm once a resolve-incomplete fixture exists.
coverage_reason: human_judgment
requirement: TRUST-04
source_plan: 48-08
result: pass
verified_live: "Operator: checked during development, forced the state via manual SQL changes; both the overridable trust gate and the non-overridable resolve gate render as specified."
note: WINDOWS.md entry #8 already marked fixed 2026-08-20; the 48-08 SUMMARY's "status=open" reference is stale.

### 7. [48-09 D1] Live reseed through the real service functions (run_import_convokit, approve_job, publish_…
expected: Live reseed through the real service functions (run_import_convokit, approve_job, publish_argument) drives all four fixtures to their target states, and recompute-trust --all reports 4 scanned / 0 changed, twice in a row — the phase's central falsifiable zero-drift claim.
rationale: must_haves' own verification: backstop truth — a zero-changed result is only as strong as the scanned count being right, which no automated check can independently prove enumerated the correct rows. The operator confirmed this live at Task 3 checkpoint step 5 (scanned=4 matching the fixture count).
coverage_reason: human_judgment
requirement: TRUST-02
source_plan: 48-09
result: pass

### 8. [48-09 D8] Finding 1: two of the four live corpus fixtures (15169, 22372) read trust_tier=uncertain r…
expected: Finding 1: two of the four live corpus fixtures (15169, 22372) read trust_tier=uncertain rather than trusted, contradicting this plan's own stated must-have. Investigated and traced to ConvoKit's genuine unattributed-speaker sentinel rows in the real corpus data — derive_tier/floor_tier/recompute_argument_tier are all working correctly; the plan's 'corpus mints a Person for every speaker' assumption does not hold universally. Not a Phase 48 code defect. Accepted by the operator as an open item at Task 3 checkpoint step 6.
rationale: A policy/expectation judgment (is an UNCERTAIN reading on real corpus data acceptable, or does it indicate a defect?), not something any automated check can adjudicate. The operator's acceptance at the Task 3 checkpoint is the closing evidence, recorded verbatim in 48-EVIDENCE.md §8.
coverage_reason: human_judgment
requirement: —
source_plan: 48-09
result: pass

### 9. [48-09 D9] derive_tier's rule 3 (source=operator, method=manual -> VERIFIED), flagged as a planner as…
expected: derive_tier's rule 3 (source=operator, method=manual -> VERIFIED), flagged as a planner assumption pending operator confirmation since plan 48-01, was confirmed by the operator on 2026-08-21 at this plan's Task 3 checkpoint. api/domain/trust.py's docstrings updated to record the confirmation; derivation logic unchanged.
rationale: A policy confirmation of an unreachable-today derivation rule requires the operator's own judgment call, not an automated check — this is exactly the flagged assumption plan 48-01 deferred to this checkpoint.
coverage_reason: human_judgment
requirement: TRUST-01
source_plan: 48-09
result: pass

### 10. [48-09 D10] Operator-requested widening of Resolve-card editability scope (editable in candidate/draft…
expected: Operator-requested widening of Resolve-card editability scope (editable in candidate/draft/unpublished, read-only only when published) observed live at Task 3 checkpoint step 2. Recorded in full (current-rule sites, requested rule, two critical caveats about non-editability CANDIDATE-only guards and recompute coverage on newly-reachable write paths, and the pre-existing-invariant note) as a new open item and a standalone todo. Deliberately NOT implemented in this plan.
rationale: A design-scope change to a deliberate, documented pre-existing invariant, requiring its own discussion/plan cycle — not something this evidence-and-closeout plan is scoped to implement or that any automated check could validate.
coverage_reason: human_judgment
requirement: —
source_plan: 48-09
result: pass
note: |
  The DELIVERABLE here is the record, and the record is complete and accurate (operator-confirmed):
  current-rule sites, the requested rule, both caveats (CANDIDATE-only guards; recompute coverage on
  newly-reachable write paths), logged as an open item plus a standalone todo. What is deferred is the
  IMPLEMENTATION, which was never in Phase 48's scope — carried forward under ## Deferred Follow-Ups,
  which is where un-built work belongs (#1921: a deferred follow-up is not a gap and must not block).

### 11. [48-10 D1] List-page (/admin/arguments) publish block/override UI at parity with the detail page — ti…
expected: List-page (/admin/arguments) publish block/override UI at parity with the detail page — tier, server message, per-blocker breakdown, override reason field, addressed to the correct row
rationale: must_haves includes a verification: backstop truth (block-reason wording reads clearly to a real operator) that no automated check in this repo can confirm.
coverage_reason: human_judgment
requirement: TRUST-05
source_plan: 48-10
result: pass
reported: "it does but I just noticed that the cancel button doesn't seem to do anything"
severity: major
resolution: "Operator applied the $state.raw(null) fix at app/src/routes/admin/arguments/+page.svelte:26 on 2026-08-21 and confirmed the Cancel button now dismisses the panel. Re-verified: 28/28 contract tests pass, npm check 0 errors."
note: Parity itself (tier, message, per-blocker counts, override field, correct row) confirmed by the operator. The defect is the Cancel affordance shipped under 48-10 D6 — see Test 14.

### 12. [48-10 D4] Detail-page publish-error rendering defect (found live at the Task 4 checkpoint): non-over…
expected: Detail-page publish-error rendering defect (found live at the Task 4 checkpoint): non-overridable resolve-gate / already-published errors now render visibly in the Status card, next to the Publish button, with no reason field; no longer leak into the case-metadata card
rationale: The original defect was found by a human in a browser, not by any automated check; the fix's acceptance is likewise the operator's own live re-verification, recorded verbatim rather than inferred from tests.
coverage_reason: human_judgment
requirement: TRUST-05
source_plan: 48-10
result: pass

### 13. [48-10 D5] Detail-page unpublish-error rendering fix (same defect, found by inspection): unpublish fa…
expected: Detail-page unpublish-error rendering fix (same defect, found by inspection): unpublish fail() payloads tagged source:'unpublish'; case-metadata card's exclusion widened via a positive !form.source test so it excludes errors from ANY tagged action, not just publish
rationale: Explicitly accepted by the operator on the strength of the static contract test alone, NOT observed live — the unpublish failure path requires the backend call itself to fail, which is not reachable from any UI state the operator can produce. This is a deliberate, recorded acceptance, not an automatic pass.
coverage_reason: human_judgment
requirement: TRUST-05
source_plan: 48-10
result: pass

### 14. [48-10 D6] Two operator-requested UI polish items: Status card date readouts now show time (formatDat…
expected: Two operator-requested UI polish items: Status card date readouts now show time (formatDateTime, matching Status History), and the list-page block panel gained a keyboard-accessible Cancel affordance that dismisses the whole panel without publishing or losing row identity
rationale: Implemented per the operator's explicit written specification (button choice, whole-panel-vs-textarea dismissal, positive-exclusion preference) and proven by static contract + npm check, but not re-walked live in a fresh browser session before this SUMMARY was written — flagged so a future reader does not assume a live pass that did not happen.
coverage_reason: human_judgment
requirement: —
source_plan: 48-10
result: pass
note: Item (a) date-with-time readouts confirmed live by the operator. Item (b) the list-page Cancel affordance is defective — tracked under gap G-48-11 (Test 11), not duplicated here.

<!-- Coverage auto-passed entries (#1602): deterministically covered by passing tests; not presented to the user. -->

### 15. [48-01 D1] One documented function (derive_tier) maps every (source, method, review_state) triple to exactly one TrustTier; first-match precedence order is fixed and total (fail-closed fallthrough).
expected: One documented function (derive_tier) maps every (source, method, review_state) triple to exactly one TrustTier; first-match precedence order is fixed and total (fail-closed fallthrough).
result: pass
source: automated
coverage_id: D1
source_plan: 48-01
verification: unit:api/tests/test_trust_domain.py::test_derive_tier_cross_product_at_unreviewed (20 cases) + test_review_state_precedence (8 cases) + test_derive_tier_fail_closed_on_unrecognised_values [pass]

### 16. [48-01 D2] floor_tier is permutation-invariant, returns UNCERTAIN on the empty sequence without raising, and returns the shared tier for single/all-equal inputs.
expected: floor_tier is permutation-invariant, returns UNCERTAIN on the empty sequence without raising, and returns the shared tier for single/all-equal inputs.
result: pass
source: automated
coverage_id: D2
source_plan: 48-01
verification: unit:api/tests/test_trust_domain.py::test_floor_tier_empty_returns_uncertain, test_floor_tier_single_element_returns_that_element, test_floor_tier_all_equal_returns_that_tier, test_floor_tier_permutation_invariant_over_mixed_list [pass]

### 17. [48-01 D3] arguments.trust_tier is the only materialized tier column, is a NOT NULL native PG enum with server_default 'uncertain', and recompute_argument_tier stores the correct floor for every writer-produced (source, method) pair, both D-11/D-12 carve-outs, the zero-constituent base case, and D-13's no-per-participant-tier rule.
expected: arguments.trust_tier is the only materialized tier column, is a NOT NULL native PG enum with server_default 'uncertain', and recompute_argument_tier stores the correct floor for every writer-produced (source, method) pair, both D-11/D-12 carve-outs, the zero-constituent base case, and D-13's no-per-participant-tier rule.
result: pass
source: automated
coverage_id: D3
source_plan: 48-01
verification: integration:api/tests/test_trust_recompute.py (18 DB-gated tests: single-provenance x5, floor, D-11, D-12 x2, D-13, unresolved participant, zero-constituent) [pass]; integration:api/tests/test_trust_tracer.py (3 tests, Task 1 tracer) [pass]

### 18. [48-01 D4] recompute_argument_tier never commits — the caller's own commit persists the value in the same transaction (48-RESEARCH.md Pitfall 2); the bulk UPDATE carries synchronize_session=False.
expected: recompute_argument_tier never commits — the caller's own commit persists the value in the same transaction (48-RESEARCH.md Pitfall 2); the bulk UPDATE carries synchronize_session=False.
result: pass
source: automated
coverage_id: D4
source_plan: 48-01
verification: integration:api/tests/test_trust_recompute.py::test_recompute_does_not_commit_until_caller_commits, test_recompute_is_idempotent_on_unchanged_data [pass]

### 19. [48-01 D5] summarize_tier_blockers reports the correct {code, count} breakdown for every blocker code (unresolved_utterance_speaker, unresolved_participant, llm_corrective_utterance, no_constituents).
expected: summarize_tier_blockers reports the correct {code, count} breakdown for every blocker code (unresolved_utterance_speaker, unresolved_participant, llm_corrective_utterance, no_constituents).
result: pass
source: automated
coverage_id: D5
source_plan: 48-01
verification: integration:api/tests/test_trust_recompute.py::test_blocker_unresolved_utterance_speaker, test_blocker_unresolved_participant, test_blocker_llm_corrective_utterance, test_blocker_no_constituents [pass]

### 20. [48-01 D6] Migration 0027 is at head on both scotus and scotus_test; the retired 'pipeline' argument_status value carries zero live rows; argument_status_log carries the two nullable override columns.
expected: Migration 0027 is at head on both scotus and scotus_test; the retired 'pipeline' argument_status value carries zero live rows; argument_status_log carries the two nullable override columns.
result: pass
source: automated
coverage_id: D6
source_plan: 48-01
verification: other:./.venv/bin/python -m alembic current (0027 (head)); Task 1 acceptance-criteria DB assertion on arguments.status='pipeline' count == 0 [pass]

### 21. [48-02 D1] delete_argument deletes every argument_status_log row for the argument before deleting the Argument row, so a DRAFT argument carrying status-log history deletes successfully instead of raising ForeignKeyViolation.
expected: delete_argument deletes every argument_status_log row for the argument before deleting the Argument row, so a DRAFT argument carrying status-log history deletes successfully instead of raising ForeignKeyViolation.
result: pass
source: automated
coverage_id: D1
source_plan: 48-02
verification: integration:api/tests/test_admin_arguments_service.py::test_delete_argument_cascades_argument_status_log [pass]; integration:api/tests/test_admin_arguments_service.py::test_delete_argument_cascades_multiple_status_log_rows [pass]

### 22. [48-02 D2] A regression test exists that fails against the pre-fix cascade and passes against the fixed one — the defect is proven by execution, not asserted by reading.
expected: A regression test exists that fails against the pre-fix cascade and passes against the fixed one — the defect is proven by execution, not asserted by reading.
result: pass
source: automated
coverage_id: D2
source_plan: 48-02
verification: other:pytest run captured verbatim in api/tests/test_admin_arguments_service.py's comment block above the cascade tests: 2 failed with sqlalchemy.exc.IntegrityError / ForeignKeyViolationError on argument_status_log_argument_id_fkey, pre-fix; 2 passed, post-fix [pass]

### 23. [48-02 D3] The DRAFT-only delete gate is unchanged (D-05): a candidate argument still returns False from delete_argument.
expected: The DRAFT-only delete gate is unchanged (D-05): a candidate argument still returns False from delete_argument.
result: pass
source: automated
coverage_id: D3
source_plan: 48-02
verification: integration:api/tests/test_admin_arguments_service.py::test_delete_argument_still_refuses_candidate [pass]

### 24. [48-02 D4] The false comment at scripts/delete_fixture_argument.py claiming a DRAFT argument can never carry a status-log row is corrected, and the stale status == pipeline reference is updated to status == candidate.
expected: The false comment at scripts/delete_fixture_argument.py claiming a DRAFT argument can never carry a status-log row is corrected, and the stale status == pipeline reference is updated to status == candidate.
result: pass
source: automated
coverage_id: D4
source_plan: 48-02
verification: other:python -c AST check: ast.get_docstring(...) does not contain 'can never have one' and does contain 'candidate' [pass]

### 25. [48-03 D1] Every public response model, and every model reachable from one through nested field annotations, is proven structurally to never declare trust_tier — the model set is derived from the live public routers' response_model= declarations rather than hardcoded, so an uncovered future public route fails the derivation guard instead of passing silently.
expected: Every public response model, and every model reachable from one through nested field annotations, is proven structurally to never declare trust_tier — the model set is derived from the live public routers' response_model= declarations rather than hardcoded, so an uncovered future public route fails the derivation guard instead of passing silently.
result: pass
source: automated
coverage_id: D1
source_plan: 48-03
verification: unit:api/tests/test_trust_public_leak_ban.py::test_public_response_model_never_declares_trust_tier (8 parametrized cases: CaseListResponse, CaseItem, ArgumentUtterancesResponse, ArgumentMetadataResponse, UtteranceResponse, SpeakerPopoverEntry, TenureEntry, PersonResponse) + test_public_model_derivation_is_non_empty [pass]

### 26. [48-03 D2] All four live public endpoints (/cases, GET /arguments/{id}/utterances, GET /arguments/{id}/speakers, GET /people/{id}) are proven, against real decoded response bodies at any nesting depth, to never expose trust_tier.
expected: All four live public endpoints (/cases, GET /arguments/{id}/utterances, GET /arguments/{id}/speakers, GET /people/{id}) are proven, against real decoded response bodies at any nesting depth, to never expose trust_tier.
result: pass
source: automated
coverage_id: D2
source_plan: 48-03
verification: integration:api/tests/test_arguments.py::test_get_utterances_returns_utterances (extended, whole-envelope sweep), test_cases_list_never_leaks_trust_tier, test_argument_speakers_never_leaks_trust_tier, test_person_detail_never_leaks_trust_tier [pass]

### 27. [48-04 D1] Every production comparison against the retired ArgumentStatusEnum.PIPELINE member in api/ and app/src now compares against CANDIDATE; surviving references are the enum declaration and deliberate dead-value test fixtures.
expected: Every production comparison against the retired ArgumentStatusEnum.PIPELINE member in api/ and app/src now compares against CANDIDATE; surviving references are the enum declaration and deliberate dead-value test fixtures.
result: pass
source: automated
coverage_id: D1
source_plan: 48-04
verification: other:grep -rn \"ArgumentStatusEnum\\.PIPELINE\" api/ pipeline/ scripts/ --include=*.py | grep -v /tests/ | grep -v models.py | grep -v comment -> empty; grep -rnE \"status *[!=]== *'pipeline'\" app/src -> empty [pass]

### 28. [48-04 D2] update_resolve_row_for_job accepts an edit on a freshly-created (candidate) argument and rejects one once the argument has left that state, with an error message naming the born state.
expected: update_resolve_row_for_job accepts an edit on a freshly-created (candidate) argument and rejects one once the argument has left that state, with an error message naming the born state.
result: pass
source: automated
coverage_id: D2
source_plan: 48-04
verification: integration:api/tests/test_admin_jobs_service.py::test_update_resolve_row_accepts_candidate_and_rejects_draft [pass]

### 29. [48-04 D3] list_resolve_rows_for_job reports editable=True for a freshly-created argument and editable=False once approved; the job detail page's readonlyMode TypeScript literal (a ninth guard site outside 48-RESEARCH.md's Python-only inventory) was also swapped.
expected: list_resolve_rows_for_job reports editable=True for a freshly-created argument and editable=False once approved; the job detail page's readonlyMode TypeScript literal (a ninth guard site outside 48-RESEARCH.md's Python-only inventory) was also swapped.
result: pass
source: automated
coverage_id: D3
source_plan: 48-04
verification: integration:api/tests/test_admin_jobs_service.py::test_list_resolve_rows_editable_flag_tracks_candidate_state [pass]; other:grep -n candidate app/src/routes/admin/pipeline/[job_id]/+page.server.ts [pass]

### 30. [48-04 D4] approve_job's double-approve guard is swapped, not removed: a freshly-created argument approves once and a second approve raises ValueError naming the already-DRAFT state.
expected: approve_job's double-approve guard is swapped, not removed: a freshly-created argument approves once and a second approve raises ValueError naming the already-DRAFT state.
result: pass
source: automated
coverage_id: D4
source_plan: 48-04
verification: integration:api/tests/test_admin_jobs_service.py::test_approve_job_accepts_freshly_created_candidate_and_rejects_second_call [pass]

### 31. [48-04 D5] All four admin_jobs writers (resolve_job, approve_job, update_resolve_row_for_job, create_person_for_job) call recompute_argument_tier before their own commit, verified by AST source-order inspection, not by eye; resolve_job calls it exactly once for the whole match batch, not once per match.
expected: All four admin_jobs writers (resolve_job, approve_job, update_resolve_row_for_job, create_person_for_job) call recompute_argument_tier before their own commit, verified by AST source-order inspection, not by eye; resolve_job calls it exactly once for the whole match batch, not once per match.
result: pass
source: automated
coverage_id: D5
source_plan: 48-04
verification: other:AST checks in this session: recompute_argument_tier present in all four function bodies; source-line index of recompute_argument_tier < db.commit in each; resolve_job's body contains exactly one recompute_argument_tier call [pass]

### 32. [48-04 D6] approve_job on a fully-resolved corpus/direct argument stamps trust_tier='trusted' (not the 'uncertain' server default); resolve_job filling the last NULL person_id moves the tier from uncertain to trusted in the same transaction as the person_id writes; a repeated writer call with no constituent change leaves the tier unchanged (idempotence/adjacency edge).
expected: approve_job on a fully-resolved corpus/direct argument stamps trust_tier='trusted' (not the 'uncertain' server default); resolve_job filling the last NULL person_id moves the tier from uncertain to trusted in the same transaction as the person_id writes; a repeated writer call with no constituent change leaves the tier unchanged (idempotence/adjacency edge).
result: pass
source: automated
coverage_id: D6
source_plan: 48-04
verification: integration:api/tests/test_admin_jobs_service.py::test_approve_job_stamps_trust_tier, test_resolve_job_recomputes_tier_when_last_speaker_resolves, test_repeated_writer_call_leaves_tier_unchanged [pass]

### 33. [48-04 D7] Candidates remain hard-excluded from /admin/arguments with no code change (D-04) — list_arguments/get_argument_stats keep their positive DRAFT/PUBLISHED/UNPUBLISHED allow-list.
expected: Candidates remain hard-excluded from /admin/arguments with no code change (D-04) — list_arguments/get_argument_stats keep their positive DRAFT/PUBLISHED/UNPUBLISHED allow-list.
result: pass
source: automated
coverage_id: D7
source_plan: 48-04
verification: other:Read api/services/admin_arguments.py this session — list_arguments/get_argument_stats' in_([DRAFT, PUBLISHED, UNPUBLISHED]) allow-list untouched by this plan [pass]

### 34. [48-05 D1] A corpus import creates an Argument at ArgumentStatusEnum.CANDIDATE (the born state) via the explicit kwarg (already correct from 48-04); a PDF ingest creates one via the model default alone, with no explicit status kwarg added.
expected: A corpus import creates an Argument at ArgumentStatusEnum.CANDIDATE (the born state) via the explicit kwarg (already correct from 48-04); a PDF ingest creates one via the model default alone, with no explicit status kwarg added.
result: pass
source: automated
coverage_id: D1
source_plan: 48-05
verification: integration:pipeline/tests/test_import_convokit_core.py::test_corpus_argument_is_born_candidate [pass]; other:AST check (Task 2 acceptance criteria): every Argument(...) call in pipeline/commands/ingest.py::_run_ingest_inner carries no status= keyword [pass]

### 35. [48-05 D2] Every argument gets exactly one ArgumentStatusLog row at creation carrying the born state, and it is the oldest row for that argument when ordered by (created_at, id) -- the same ordering get_argument_detail uses (TRUST-03 ordering edge).
expected: Every argument gets exactly one ArgumentStatusLog row at creation carrying the born state, and it is the oldest row for that argument when ordered by (created_at, id) -- the same ordering get_argument_detail uses (TRUST-03 ordering edge).
result: pass
source: automated
coverage_id: D2
source_plan: 48-05
verification: integration:pipeline/tests/test_import_convokit_core.py::test_corpus_birth_writes_one_candidate_status_log_row [pass]

### 36. [48-05 D3] A corpus argument's stored trust_tier reads TRUSTED at import time (not the UNCERTAIN server default) once every constituent resolves; a PDF-ingested argument with zero utterances reads UNCERTAIN, matching the fail-closed default, proving the ingest writer path is wired rather than lucky.
expected: A corpus argument's stored trust_tier reads TRUSTED at import time (not the UNCERTAIN server default) once every constituent resolves; a PDF-ingested argument with zero utterances reads UNCERTAIN, matching the fail-closed default, proving the ingest writer path is wired rather than lucky.
result: pass
source: automated
coverage_id: D3
source_plan: 48-05
verification: integration:pipeline/tests/test_import_convokit_core.py::test_corpus_argument_tier_is_trusted_on_arrival [pass]; other:AST check (Task 2 acceptance criteria): recompute_argument_tier appears exactly once in ingest.py's _run_ingest_inner, parse.py, and resolve.py each [pass]

### 37. [48-05 D4] Re-running the corpus importer for a conversation that already has an argument creates no second Argument row, no second born-state status-log row, and leaves the stored tier unchanged (TRUST-03 adjacency edge; the idempotent-SKIP early return is preserved).
expected: Re-running the corpus importer for a conversation that already has an argument creates no second Argument row, no second born-state status-log row, and leaves the stored tier unchanged (TRUST-03 adjacency edge; the idempotent-SKIP early return is preserved).
result: pass
source: automated
coverage_id: D4
source_plan: 48-05
verification: integration:pipeline/tests/test_import_convokit_core.py::test_corpus_reimport_adds_no_second_birth_row [pass]

### 38. [48-05 D5] The corpus import, PDF ingest, parse, and resolve commands each call recompute_argument_tier inside their own get_session() block, strictly before that block's clean exit -- no session.commit() was introduced anywhere -- so the tier commits atomically with the writes that produced it.
expected: The corpus import, PDF ingest, parse, and resolve commands each call recompute_argument_tier inside their own get_session() block, strictly before that block's clean exit -- no session.commit() was introduced anywhere -- so the tier commits atomically with the writes that produced it.
result: pass
source: automated
coverage_id: D5
source_plan: 48-05
verification: other:AST checks (Task 1/2 acceptance criteria): ArgumentStatusLog precedes recompute_argument_tier in _import_conversation's source order; grep -c session.commit() returns 0 for ingest.py/parse.py/resolve.py [pass]

### 39. [48-05 D6] Full pipeline and full-repo test suites are green with exactly the one pre-existing known-expected failure (test_admin_detail_contract_does_declare_trust_tier, tracked since 48-03, resolves at 48-07) and zero new/unexpected failures.
expected: Full pipeline and full-repo test suites are green with exactly the one pre-existing known-expected failure (test_admin_detail_contract_does_declare_trust_tier, tracked since 48-03, resolves at 48-07) and zero new/unexpected failures.
result: pass
source: automated
coverage_id: D6
source_plan: 48-05
verification: other:./.venv/bin/python -m pytest -q -> 1 failed (known-expected), 1136 passed, 4 skipped, 5 xfailed [pass]

### 40. [48-06 D1] recompute-trust --all scans every argument, recomputes each through the shared api.services.trust.recompute_argument_tier service, and reports an accurate scanned/unchanged/changed summary plus one line per changed argument naming its id, old tier, and new tier.
expected: recompute-trust --all scans every argument, recomputes each through the shared api.services.trust.recompute_argument_tier service, and reports an accurate scanned/unchanged/changed summary plus one line per changed argument naming its id, old tier, and new tier.
result: pass
source: automated
coverage_id: D1
source_plan: 48-06
verification: integration:pipeline/tests/test_recompute_trust.py::test_recompute_all_repairs_drifted_tier [pass]

### 41. [48-06 D2] Re-running --all after a repair reports changed == 0 — the idempotence/adjacency edge plan 48-09's verification depends on.
expected: Re-running --all after a repair reports changed == 0 — the idempotence/adjacency edge plan 48-09's verification depends on.
result: pass
source: automated
coverage_id: D2
source_plan: 48-06
verification: integration:pipeline/tests/test_recompute_trust.py::test_recompute_all_is_idempotent [pass]

### 42. [48-06 D3] --dry-run reports what would change without writing it — the stored tier is provably untouched afterward.
expected: --dry-run reports what would change without writing it — the stored tier is provably untouched afterward.
result: pass
source: automated
coverage_id: D3
source_plan: 48-06
verification: integration:pipeline/tests/test_recompute_trust.py::test_recompute_dry_run_reports_without_writing [pass]

### 43. [48-06 D4] --argument-id scopes the repair to exactly one argument, leaving a second corrupted argument's tier untouched.
expected: --argument-id scopes the repair to exactly one argument, leaving a second corrupted argument's tier untouched.
result: pass
source: automated
coverage_id: D4
source_plan: 48-06
verification: integration:pipeline/tests/test_recompute_trust.py::test_recompute_single_argument_scopes_to_that_argument [pass]

### 44. [48-06 D5] --argument-id for a nonexistent id raises ValueError naming the id rather than reporting a vacuous success; --all against an empty database reports scanned == 0, changed == 0 rather than failing or reporting success vacuously (the unclassified TRUST-02 edge probe's detector).
expected: --argument-id for a nonexistent id raises ValueError naming the id rather than reporting a vacuous success; --all against an empty database reports scanned == 0, changed == 0 rather than failing or reporting success vacuously (the unclassified TRUST-02 edge probe's detector).
result: pass
source: automated
coverage_id: D5
source_plan: 48-06
verification: integration:pipeline/tests/test_recompute_trust.py::test_recompute_unknown_argument_id_raises, test_recompute_all_on_empty_database_reports_zero [pass]

### 45. [48-06 D6] The command derives nothing of its own (imports api.services.trust, no re-derivation logic) and has no HTTP surface — offline CLI only per CLAUDE.md.
expected: The command derives nothing of its own (imports api.services.trust, no re-derivation logic) and has no HTTP surface — offline CLI only per CLAUDE.md.
result: pass
source: automated
coverage_id: D6
source_plan: 48-06
verification: other:AST check: 'api.services.trust' in the module's ImportFrom targets, no fastapi import; grep -rn recompute api/routers/ returns no lines [pass]

### 46. [48-06 D7] Full-repo test suite remains green with exactly the one pre-existing known-expected failure (test_admin_detail_contract_does_declare_trust_tier, resolves at 48-07) and zero new/unexpected failures.
expected: Full-repo test suite remains green with exactly the one pre-existing known-expected failure (test_admin_detail_contract_does_declare_trust_tier, resolves at 48-07) and zero new/unexpected failures.
result: pass
source: automated
coverage_id: D7
source_plan: 48-06
verification: other:./.venv/bin/python -m pytest api/tests pipeline/tests tests -q -> 1 failed (known-expected), 1146 passed, 5 xfailed, 0 unexpected [pass]

### 47. [48-07 D1] publish_argument evaluates the non-overridable resolved_at gate strictly before the overridable UNCERTAIN trust gate, in both the source (AST/line-index assertions) and behaviorally (an unresolved, uncertain-tier argument is blocked by the resolve gate regardless of override_reason).
expected: publish_argument evaluates the non-overridable resolved_at gate strictly before the overridable UNCERTAIN trust gate, in both the source (AST/line-index assertions) and behaviorally (an unresolved, uncertain-tier argument is blocked by the resolve gate regardless of override_reason).
result: pass
source: automated
coverage_id: D1
source_plan: 48-07
verification: unit:api/tests/test_published_gate.py::TestPublishOverrideGateSourceLevel::test_resolve_gate_precedes_trust_gate_in_publish_argument [pass]; integration:api/tests/test_published_gate.py::test_publish_blocked_when_resolve_incomplete_even_with_override_reason [pass]

### 48. [48-07 D2] A blocked publish (UNCERTAIN tier, no usable reason) raises TrustGateBlocked carrying the tier plus a non-empty, structured blocker breakdown (not a bare tier name), and writes nothing — published_at stays NULL, status is unchanged, no ArgumentStatusLog row is added.
expected: A blocked publish (UNCERTAIN tier, no usable reason) raises TrustGateBlocked carrying the tier plus a non-empty, structured blocker breakdown (not a bare tier name), and writes nothing — published_at stays NULL, status is unchanged, no ArgumentStatusLog row is added.
result: pass
source: automated
coverage_id: D2
source_plan: 48-07
verification: integration:api/tests/test_published_gate.py::test_publish_blocked_when_uncertain_without_reason [pass]

### 49. [48-07 D3] An override reason that is empty, missing, or whitespace-only (including a non-breaking space) is rejected server-side after .strip(), independently of any UI affordance, with a distinguishable blank_override_reason code separate from the no-reason-supplied TrustGateBlocked case.
expected: An override reason that is empty, missing, or whitespace-only (including a non-breaking space) is rejected server-side after .strip(), independently of any UI affordance, with a distinguishable blank_override_reason code separate from the no-reason-supplied TrustGateBlocked case.
result: pass
source: automated
coverage_id: D3
source_plan: 48-07
verification: integration:api/tests/test_published_gate.py::test_publish_blocked_when_override_reason_is_whitespace_only (4 parametrized whitespace forms) [pass]

### 50. [48-07 D4] A successful override writes its ArgumentStatusLog row with override_reason set to the stripped text and trust_tier_at_transition set to the tier at that moment; a normal publish of a non-uncertain argument with no reason leaves both columns NULL — the override path is not accidentally mandatory.
expected: A successful override writes its ArgumentStatusLog row with override_reason set to the stripped text and trust_tier_at_transition set to the tier at that moment; a normal publish of a non-uncertain argument with no reason leaves both columns NULL — the override path is not accidentally mandatory.
result: pass
source: automated
coverage_id: D4
source_plan: 48-07
verification: integration:api/tests/test_published_gate.py::test_publish_succeeds_with_override_and_logs_reason_and_tier, test_publish_without_override_leaves_audit_columns_null [pass]

### 51. [48-07 D5] The override is per publish attempt and never sticky — an unpublish then a republish while still UNCERTAIN is blocked again and requires a fresh reason, writing a second distinct override log row; no persistent per-argument exemption flag exists anywhere in the schema or service.
expected: The override is per publish attempt and never sticky — an unpublish then a republish while still UNCERTAIN is blocked again and requires a fresh reason, writing a second distinct override log row; no persistent per-argument exemption flag exists anywhere in the schema or service.
result: pass
source: automated
coverage_id: D5
source_plan: 48-07
verification: integration:api/tests/test_published_gate.py::test_override_is_not_sticky_across_republish [pass]; other:grep -rn \"exemption|override_sticky|publish_override_flag\" api/ --include=*.py returns no lines [pass]

### 52. [48-07 D6] GET /api/admin/arguments/{id} returns trust_tier; the admin list endpoints are untouched; trust_tier never appears in any public response.
expected: GET /api/admin/arguments/{id} returns trust_tier; the admin list endpoints are untouched; trust_tier never appears in any public response.
result: pass
source: automated
coverage_id: D6
source_plan: 48-07
verification: unit:api/tests/test_trust_public_leak_ban.py::test_admin_detail_contract_does_declare_trust_tier (now passing — the target this plan turns green) and the existing public leak-ban tests (unmodified, still green) [pass]; integration:api/tests/test_admin_arguments_routes.py::test_publish_route_with_override_reason_returns_200_and_trust_tier [pass]

### 53. [48-07 D7] publish_argument, unpublish_argument, and update_participant_side each recompute the tier in their own transaction before their own commit — the tier stays live after publish/unpublish/participant edits.
expected: publish_argument, unpublish_argument, and update_participant_side each recompute the tier in their own transaction before their own commit — the tier stays live after publish/unpublish/participant edits.
result: pass
source: automated
coverage_id: D7
source_plan: 48-07
verification: unit:api/tests/test_published_gate.py::TestPublishOverrideGateSourceLevel::test_publish_argument_recomputes_tier_before_committing, test_unpublish_and_participant_side_update_recompute_before_committing [pass]

### 54. [48-08 D1] A blocked publish (uncertain_tier_blocked) renders the tier and one human sentence per blocker code with its count via blockerSentence, not a bare tier name.
expected: A blocked publish (uncertain_tier_blocked) renders the tier and one human sentence per blocker code with its count via blockerSentence, not a bare tier name.
result: pass
source: automated
coverage_id: D1
source_plan: 48-08
verification: other:api/tests/test_phase48_publish_override_ui_contract.py (blockerSentence maps all four codes; publishBlocked panel assertions) [pass]; manual_procedural:Operator browser walkthrough step 4 (approved) [pass]

### 55. [48-08 D2] The override_reason textarea re-submits the same ?/publish action; a whitespace-only reason is rejected server-side and rendered distinctly from the original block; a real reason publishes and is not sticky across a subsequent unpublish/republish.
expected: The override_reason textarea re-submits the same ?/publish action; a whitespace-only reason is rejected server-side and rendered distinctly from the original block; a real reason publishes and is not sticky across a subsequent unpublish/republish.
result: pass
source: automated
coverage_id: D2
source_plan: 48-08
verification: other:api/tests/test_phase48_publish_override_ui_contract.py (override_reason textarea inside a ?/publish form guarded by form?.publishBlocked) [pass]; manual_procedural:Operator browser walkthrough steps 5-7 (approved) [pass]

### 56. [48-08 D4] The candidate born state renders its own badge label instead of falling through to the retired 'Pipeline' label.
expected: The candidate born state renders its own badge label instead of falling through to the retired 'Pipeline' label.
result: pass
source: automated
coverage_id: D4
source_plan: 48-08
verification: other:api/tests/test_phase48_publish_override_ui_contract.py (no retired 'pipeline' literal remains in +page.svelte) [pass]

### 57. [48-08 D5] The Publish control's visibility rule (draft or unpublished only) is unchanged, and no new component/screen/design-system import was introduced.
expected: The Publish control's visibility rule (draft or unpublished only) is unchanged, and no new component/screen/design-system import was introduced.
result: pass
source: automated
coverage_id: D5
source_plan: 48-08
verification: other:api/tests/test_phase48_publish_override_ui_contract.py (visibility-rule grep, component-import-count grep) [pass]

### 58. [48-09 D2] The Complexity and Mid-pipeline fixtures are born at status=candidate with exactly one born-state argument_status_log row each, oldest by construction; the Draft and Published fixtures show the birth transition as their oldest status-log entry after the id-ordering fix.
expected: The Complexity and Mid-pipeline fixtures are born at status=candidate with exactly one born-state argument_status_log row each, oldest by construction; the Draft and Published fixtures show the birth transition as their oldest status-log entry after the id-ordering fix.
result: pass
source: automated
coverage_id: D2
source_plan: 48-09
verification: integration:pipeline/tests/test_import_convokit_core.py (39 passed) [pass]; other:48-EVIDENCE.md §3 fixture state table (direct DB query, post-reseed) [pass]

### 59. [48-09 D3] The two-gate publish (non-overridable resolved_at gate, then the overridable UNCERTAIN trust gate with a required, permanently-logged, non-sticky reason) is proven both by pytest and by the live Published fixture reaching published through the real service.
expected: The two-gate publish (non-overridable resolved_at gate, then the overridable UNCERTAIN trust gate with a required, permanently-logged, non-sticky reason) is proven both by pytest and by the live Published fixture reaching published through the real service.
result: pass
source: automated
coverage_id: D3
source_plan: 48-09
verification: integration:api/tests/test_published_gate.py (31 passed) [pass]

### 60. [48-09 D4] Operator override path (required non-blank reason, structured 422 codes, audit-row contents) proven at the route level; the admin detail contract's trust_tier exposure is confirmed live on the Draft/Published fixtures without any leak onto public responses.
expected: Operator override path (required non-blank reason, structured 422 codes, audit-row contents) proven at the route level; the admin detail contract's trust_tier exposure is confirmed live on the Draft/Published fixtures without any leak onto public responses.
result: pass
source: automated
coverage_id: D4
source_plan: 48-09
verification: integration:api/tests/test_admin_arguments_routes.py (29 passed) [pass]; manual_procedural:Task 3 checkpoint step 4 (operator browser walkthrough) — Published fixture publicly visible with no trust/tier/provenance on the page [pass]

### 61. [48-09 D5] delete_argument's argument_status_log cascade fix (D-22, carried defect) and the public trust-tier leak ban (D-23) both re-confirmed green at phase close.
expected: delete_argument's argument_status_log cascade fix (D-22, carried defect) and the public trust-tier leak ban (D-23) both re-confirmed green at phase close.
result: pass
source: automated
coverage_id: D5
source_plan: 48-09
verification: integration:api/tests/test_admin_arguments_service.py::test_delete_argument_cascades_argument_status_log, ::test_delete_argument_cascades_multiple_status_log_rows (2 passed); api/tests/test_trust_public_leak_ban.py (11 passed) [pass]

### 62. [48-09 D6] Full-suite phase gate: 1209 passed / 5 xfailed / 0 failed / 0 skipped (up from the 2026-08-18 baseline of 1049); build (compileall) clean; frontend check (npm run check) 0 errors / 36 pre-existing warnings; both PIPELINE-born-state completeness greps empty; 32 deliberate test-fixture references confirmed still present for the retired enum value.
expected: Full-suite phase gate: 1209 passed / 5 xfailed / 0 failed / 0 skipped (up from the 2026-08-18 baseline of 1049); build (compileall) clean; frontend check (npm run check) 0 errors / 36 pre-existing warnings; both PIPELINE-born-state completeness greps empty; 32 deliberate test-fixture references confirmed still present for the retired enum value.
result: pass
source: automated
coverage_id: D6
source_plan: 48-09
verification: other:./.venv/bin/python -m pytest (48-EVIDENCE.md §6a, second/final run); python3 -m compileall -q pipeline api scripts tests alembic; cd app && npm run check [pass]

### 63. [48-09 D7] Status History display-ordering bug found via this plan's own live evidence-gathering (Finding 2, first half): get_argument_detail's argument_status_log query ordered by created_at first, which can invert insertion order for any writer batching a later write into a transaction opened earlier by an unrelated read. Fixed to order by id ASC; regression test confirmed RED against the old ordering and GREEN against the fix; operator re-confirmed correct rendering live at Task 3 checkpoint step 3.
expected: Status History display-ordering bug found via this plan's own live evidence-gathering (Finding 2, first half): get_argument_detail's argument_status_log query ordered by created_at first, which can invert insertion order for any writer batching a later write into a transaction opened earlier by an unrelated read. Fixed to order by id ASC; regression test confirmed RED against the old ordering and GREEN against the fix; operator re-confirmed correct rendering live at Task 3 checkpoint step 3.
result: pass
source: automated
coverage_id: D7
source_plan: 48-09
verification: integration:api/tests/test_admin_arguments_service.py::test_get_argument_detail_status_log_orders_by_id_not_created_at [pass]; manual_procedural:Task 3 checkpoint step 3 (operator browser walkthrough, confirmed after commit 1b7564a78) [pass]

### 64. [48-10 D2] Passive per-row trust-tier badge on the list page, never wired to any control, Publish button never disabled by tier
expected: Passive per-row trust-tier badge on the list page, never wired to any control, Publish button never disabled by tier
result: pass
source: automated
coverage_id: D2
source_plan: 48-10
verification: other:api/tests/test_phase48_list_publish_override_ui_contract.py::test_passive_tier_badge_renders_per_row, ::test_publish_button_never_disabled_based_on_tier_or_block_state [pass]

### 65. [48-10 D3] Unpublish genuinely hides an argument from all three public read paths (get_cases, get_argument_with_utterances, get_argument_speakers)
expected: Unpublish genuinely hides an argument from all three public read paths (get_cases, get_argument_with_utterances, get_argument_speakers)
result: pass
source: automated
coverage_id: D3
source_plan: 48-10
verification: integration:api/tests/test_phase48_unpublish_visibility.py [pass]; manual_procedural:48-10 Task 4 checkpoint step 7 (operator browser walkthrough, prior session) [pass]

## Deferred Follow-Ups

- test: 10
  idea: "Widen Resolve-card editability scope: editable in candidate/draft/unpublished, read-only only when published. Caveats: existing non-editability guards are CANDIDATE-only; recompute coverage must extend to newly-reachable write paths. Needs its own discuss/plan cycle."
  deferred_at: 2026-08-21

## Summary

total: 65
passed: 65
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

- gap_id: G-48-11
  truth: "The list-page block panel's Cancel affordance dismisses the whole panel without publishing and without losing row identity (48-10 D6)."
  status: resolved
  reason: "User reported: it does but I just noticed that the cancel button doesn't seem to do anything"
  severity: major
  test: 11
  resolved_by: "operator-applied fix — app/src/routes/admin/arguments/+page.svelte:26 changed to $state.raw(null)"
  resolved_at: 2026-08-21
  root_cause: "Svelte 5 $state deep-proxy identity trap. `dismissedForm` is declared `let dismissedForm: unknown = $state(null)` (app/src/routes/admin/arguments/+page.svelte:26). In Svelte 5.30, assigning a plain object to a $state variable wraps it in a deep reactive proxy, so `dismissedForm = form` stores a PROXY of form, not form itself. The panel guard `form !== dismissedForm` (line 483) therefore compares the raw prop object against its own proxy — always unequal — so the guard never goes false and the panel never dismisses. Empirically confirmed: `proxy(form) !== form` is true while contents are identical."
  artifacts:
    - path: "app/src/routes/admin/arguments/+page.svelte"
      issue: "line 26 — `$state(null)` proxies the assigned `form` object, breaking the reference comparison the dismissal design depends on"
    - path: "api/tests/test_phase48_list_publish_override_ui_contract.py"
      issue: "tests are purely structural string greps (guard text, button element, type=\"button\", accessible name) and never execute the component, so a runtime identity bug is invisible to them — the reason D6 was flagged as not-re-walked-live"
  missing:
    - "Change line 26 to `let dismissedForm: unknown = $state.raw(null);` — $state.raw does not proxy the assigned value, preserving the reference identity the design comment explicitly relies on (re-clicking Publish yields a NEW form object, so the panel correctly reappears)."
    - "Add a behavioral test that actually mounts the component and asserts the panel disappears on Cancel and reappears on a subsequent Publish — the existing structural greps cannot catch this class of defect."
  debug_session: ""
