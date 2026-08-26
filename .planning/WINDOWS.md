---
schema_version: 1
open_count: 23
waived_count: 0
fixed_count: 7
total_count: 30
last_updated: 2026-08-26T15:35:23.632Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 39 | stub | app/src/lib/components/SpeakerPopover.svelte |  | Advocate descriptor slot renders literal 'Coming soon' — intentional per D-16/39-UI-SPEC.md; no per-advocate descriptor extraction pipeline exists yet, deferred to a future phase | open |  | 2026-07-28T16:34:59.919Z |  |
| 2 | 44 | unrun-verify | app/src/lib/components/ResolveCard.svelte |  | Visual check against resolve-speakers-panel.png (Raw Label badge wrap on a synthetic long label, pre-filled combobox visibility, always-present Descriptor cell) deferred to Plan 44-04's checkpoint per 44-02-PLAN.md verification item 5 — structural/grep-based contract tests pass now, but no visual render has been eyeballed yet. | open |  | 2026-08-01T18:19:47.948Z |  |
| 3 | 47 | unrun-verify | tests/test_pytest_isolation_invocation_shapes.py |  | Task 3's verify command (pytest tests/test_pytest_isolation_invocation_shapes.py) cannot pass until plans 47-02/47-03 land -- api/tests/test_db_isolation_probe.py's autouse _api_lifespan fixture imports api.main -> api.routers.admin, which still imports the retired PipelineRun symbol (47-03's scoped file). | fixed |  | 2026-08-17T21:03:40.591Z | 2026-08-17T21:30:56.342Z |
| 4 | 47 | unrun-verify | tests/test_pytest_isolation_invocation_shapes.py |  | bare-testpaths-driven shape still exits non-zero after 47-03 -- full-tree collection hits ImportError: cannot import name 'PipelineRun' in test-body-only references (api/tests/test_admin_dev_routes.py:331, pipeline/tests/test_delete_fixture_argument.py, test_diff_corpus_fixture.py, test_import_convokit_core.py, test_import_convokit_utterances.py), all owned by 47-04/47-05's test-suite conversion, not 47-03's files_modified. The other 2 of 3 parametrized shapes (explicit-single-file, explicit-multi-path) pass cleanly now that 47-03 converted api/routers/admin.py. | fixed |  | 2026-08-17T21:31:05.797Z | 2026-08-17T22:21:40.026Z |
| 5 | 47 | deviation | api/tests/test_phase44_argument_role_roundtrip.py |  | Pre-existing SideEnum identity mismatch under bare full-suite pytest -q (testpaths order reimports api.* modules via tests/test_admin_router.py before this file runs) - unrelated to Phase 47 import_run rename, both files predate Phase 47. See deferred-items.md. | open |  | 2026-08-17T22:21:11.348Z |  |
| 6 | 48 | unmet-truth | api/tests/test_trust_public_leak_ban.py |  | test_admin_detail_contract_does_declare_trust_tier fails until plan 48-07 lands trust_tier on ArgumentDetail (D-20); documented as expected/tracked in 48-03-SUMMARY.md, re-run at 48-07 close | fixed |  | 2026-08-19T13:05:36.138Z | 2026-08-19T15:55:57.028Z |
| 7 | 48 | deviation | pipeline/commands/import_convokit.py | 515 | 48-04 Task 1 (Rule 3 blocking-fix) flipped this birth-write status kwarg from PIPELINE to CANDIDATE ahead of plan 48-05's own scheduled edit, to keep the phase 48-04 guard swap internally consistent; 48-05 still owns the rest of this file's birth-logging/recompute scope and will find this one line already done. | fixed |  | 2026-08-19T14:41:22.505Z | 2026-08-19T15:04:51.300Z |
| 8 | 48 | unrun-verify | app/src/routes/admin/arguments/[id]/+page.svelte |  | 48-08 checkpoint step 8 not executed: no argument with an incomplete resolve step was available, so the non-overridable resolved_at gate (D-14) rendering with NO override field offered is unverified in a browser. Steps 1-7 passed. Re-verify when a resolve-incomplete fixture exists. | fixed |  | 2026-08-19T23:33:18.102Z | 2026-08-20T16:43:58.653Z |
| 9 | 48 | deviation | api/services/admin_arguments.py | 448 | get_argument_detail's status-log query ordered by created_at first, which can invert insertion order for a writer that reuses a long-lived session/transaction (found live via 48-09's reseed evidence); fixed to order by id ASC in commit 1b7564a78, regression-tested. Underlying stale-created_at STORAGE cause in reset_to_fixture remains open, tracked separately. | open |  | 2026-08-21T14:27:04.542Z |  |
| 10 | 48 | unmet-truth | .planning/phases/48-trust-lifecycle/48-09-PLAN.md |  | Finding 1 (48-EVIDENCE.md): must_haves.truths expected all four corpus fixtures to read trust_tier=trusted after reseed; 15169 and 22372 read uncertain due to ConvoKit's own unattributed-speaker sentinel rows. derive_tier is correct -- the plan's 'corpus mints a Person for every speaker' assumption does not hold universally. Accepted by operator as an open item, not a defect, at the Task 3 checkpoint (2026-08-21). | open |  | 2026-08-21T14:27:06.606Z |  |
| 11 | 49 | deviation | api/services/admin_jobs.py |  | resolve_job/update_resolve_row_for_job never stamp ArgumentParticipant.source/method; 49-01's D-18 change now floors these to UNCERTAIN. 2 test failures in api/tests/test_admin_jobs_service.py, out of 49-02 scope — see .planning/phases/49-review-model/deferred-items.md | fixed |  | 2026-08-23T12:43:33.463Z | 2026-08-23T14:10:35.664Z |
| 12 | 49 | deviation | api/services/admin_review.py |  | _argument_attention_predicate had only 3 legs (needs_review, unresolved_participant, degraded_tier) -- no leg for 'a constituent has an open value_discrepancy', even though _person_attention_predicate already had the equivalent leg for people. Found live during 49-06's own D-32 walkthrough: an operator-edited, already-resolved participant that a lower-authority re-import disagreed with was invisible in /admin/review. Fixed same-plan: leg 4 added, list_review_queue_arguments' constituent-inclusion check widened to match, 2 new regression tests. | fixed |  | 2026-08-23T16:11:33.813Z | 2026-08-23T16:11:33.813Z |
| 13 | 49 | deviation | .planning/phases/49-review-model/49-RESEARCH.md |  | Pitfall 4's premise ('no live corpus path can produce an unresolved speaker because _resolve_person always resolves-or-creates') is false -- verified against the live dev DB before 49-06 started: argument 1788 had 11 person_id-IS-NULL participants from a job parked pre-resolve. The dev-only seeder (D-33a) was built anyway, justified instead by its own standalone value (a deterministic, repeatable fixture for 26-UAT/14-UAT), not by the false claim. It WAS initially restated in the shipped docstring of api/services/admin_dev.py::seed_unresolved_speaker_fixture despite the SUMMARY claiming otherwise; the orchestrator corrected that docstring on 2026-08-23. | open |  | 2026-08-23T16:13:01.505Z |  |
| 14 | 49 | unrun-verify | app/src/routes/admin/review/+page.svelte |  | 49-01's Confirm-vs-Resolve-speaker-link conditional rendering (tracer feedback gate defect 2 fix) has not been re-verified in a live browser since the fix -- unit/integration-tested only. See 49-01-SUMMARY.md coverage D6. | open |  | 2026-08-23T16:13:12.844Z |  |
| 15 | 49 | unrun-verify | app/src/lib/components/CreatePersonPopover.svelte |  | 49-03's CreatePersonPopover Bench/Advocate side-inheritance walkthrough (toggle row to Bench, open Create-new-bench-person, confirm Bench pre-selected, create person, confirm Resolved As shows the name; repeat on Advocate) was never run in a browser -- credential-access denial. See 49-03-SUMMARY.md coverage D1/D2. | open |  | 2026-08-23T16:13:13.173Z |  |
| 16 | 49 | unrun-verify | app/src/routes/admin/help/+page.svelte |  | 49-03's /admin/help visual + apolitical read-through (badge colors, 375px width, no ranking language) was never run in a browser -- credential-access denial. See 49-03-SUMMARY.md coverage D4. | open |  | 2026-08-23T16:13:13.491Z |  |
| 17 | 49 | unrun-verify | app/src/routes/admin/review/+page.svelte |  | 49-05's Task 2 seven-item browser walkthrough of the full /admin/review screen (tabs, filter composition/back-button/active-filter-indicator, expand/collapse incl. zero-constituent fallback, Confirm/Confirm-as-unattributable/Re-flag actions with D-26 stay-visible behavior, five dashboard StatCards in one row, StatCard singular/zero-state text, no horizontal scroll at 375px) was never run in a browser -- credential-access denial. See 49-05-SUMMARY.md coverage D4/D5. | open |  | 2026-08-23T16:13:13.738Z |  |
| 18 | 49 | unrun-verify | app/src/routes/admin/arguments/[id]/+page.svelte |  | 26-UAT Test 26 (unresolved-advocate placeholder + Save gate) -- 49-06's seeder makes the underlying side=UNKNOWN/person_id=NULL data state reachable and script/API-confirmed live on the dev DB, but the actual on-screen render (placeholder text, Save-button disabled state) was never observed in a browser -- credential-access denial. See 26-UAT.md Test 26's phase_49_06_update. | open |  | 2026-08-23T16:19:41.333Z |  |
| 19 | 49 | unrun-verify | app/src/lib/components/ChatBubble.svelte |  | 14-UAT Test 8 (non-resolved-utterance avatar) -- 49-06's seeder now also nulls the matching Utterance.person_id rows, script/API-confirmed live on the dev DB, but the argument must also be PUBLISHED to reach the public chat page (a step this seeder deliberately does not perform) and the actual on-screen non-interactive-avatar render was never observed -- credential-access denial. See 14-UAT.md Test 8's phase_49_06_update. | open |  | 2026-08-23T16:19:41.608Z |  |
| 20 | 49 | unrun-verify | app/src/routes/admin/review/+page.svelte |  | D-32's live authority-conflict walkthrough -- fully verified end-to-end via a repeatable script against the live dev DB (operator edit survives, corpus re-import rejected+recorded, discrepancy visible via the API, reflag closes it) in 49-EVIDENCE.md, including finding and fixing a real gap (WINDOWS #12). The actual browser rendering (Discrepancy badge color/placement, click behavior) was never observed -- credential-access denial. | open |  | 2026-08-23T16:19:41.894Z |  |
| 21 | 49 | unrun-verify | app/src/routes/admin/+page.svelte |  | The new 'Seed unresolved speaker' Dev Tools button and its success line were never observed in a browser -- credential-access denial. Backend endpoint and the form action's error-mapping are fully tested; only the button's rendering/behavior is unconfirmed. | open |  | 2026-08-23T16:19:42.185Z |  |
| 22 | 49 | unrun-verify | app/src/lib/components/CreatePersonPopover.svelte |  | WR-01 browser walkthrough (49-09 Task 1 human-check) NOT OBSERVED — sandbox denied .env access for ADMIN_USERNAME/ADMIN_PASSWORD/SESSION_SECRET | open |  | 2026-08-24T20:00:45.872Z |  |
| 23 | 49 | unrun-verify | app/src/routes/admin/arguments/[id]/+page.svelte |  | Speakers-card published-lock visual verification (49-09 Task 3 human-check) NOT OBSERVED — sandbox denied .env access for ADMIN_USERNAME/ADMIN_PASSWORD/SESSION_SECRET | open |  | 2026-08-24T20:00:46.273Z |  |
| 24 | 49 | unrun-verify | api/tests/test_phase49_participant_side_contract.py |  | Task 1 human-check (Resolve-card regression walk: toggle behavior, person-clear on real boundary crossing, unchanged labels) not observed in this session — browser tooling unavailable to executor | open |  | 2026-08-24T22:49:21.712Z |  |
| 25 | 49 | unrun-verify | app/src/routes/admin/arguments/[id]/+page.svelte |  | Task 3 six-item Speakers-card convergence human-check walk not observed in this session — browser tooling unavailable to executor | open |  | 2026-08-24T22:49:22.058Z |  |
| 26 | 49 | deviation | app/src/routes/admin/arguments/+page.svelte |  | New finding during 49-12 (G-49-5c) live measurement: /admin/arguments overflows at 375px (scrollWidth 680 vs clientWidth 375) via an unwrapped <table> with no overflow-x container -- separate, pre-existing cause independent of AdminSubNav; out of scope for 49-12 (files_modified did not include this page). Not fixed. | open |  | 2026-08-25T10:54:02.125Z |  |
| 27 | 49 | deviation | app/src/routes/admin/people/+page.svelte |  | New finding during 49-12 (G-49-5c) live measurement: /admin/people overflows at 375px (scrollWidth 403 vs clientWidth 375) via an unwrapped <table> with no overflow-x container -- separate, pre-existing cause independent of AdminSubNav. Was previously masked by AdminSubNav's larger 423px overflow (both pegged the page at the same scrollWidth); only became independently visible after 49-12 fixed the sub-nav. Out of scope for 49-12 (files_modified did not include this page). Not fixed. | open |  | 2026-08-25T10:54:09.338Z |  |
| 28 | 49 | unrun-verify | app/src/routes/admin/arguments/[id]/+page.svelte |  | Task 3 browser human-check (5 items) not observed — no browser tool available to the executor; see 49-11-SUMMARY.md Human-Check Items section | open |  | 2026-08-25T11:18:44.159Z |  |
| 29 | 50 | deviation | pipeline/commands/import_convokit.py | 636 | _reconcile_conversation's compare-and-write body is deferred to plan 50-05 by design (50-01-PLAN.md Task 3 scope); it currently only establishes the digest-compare branch and writes nothing on a real content mismatch. | open |  | 2026-08-26T13:51:01.301Z |  |
| 30 | 50-unified-import-path | unrun-verify | app/src/routes/admin/review/+page.svelte |  | 50-04 Task 2 human-check walkthrough not performed: Approve on a candidate corpus argument, tab/filter survival on redirect, Approve button absence post-transition, publish-after-approve, and no-truncation of a discrepancy value at 1280px and narrow viewports — no browser tool / .env admin credential access available to this executor (same constraint as 49-01/49-03/49-05/49-06). | open |  | 2026-08-26T15:35:23.632Z |  |

````json
[
  {
    "id": 1,
    "kind": "stub",
    "phase": "39",
    "file": "app/src/lib/components/SpeakerPopover.svelte",
    "line": null,
    "description": "Advocate descriptor slot renders literal 'Coming soon' — intentional per D-16/39-UI-SPEC.md; no per-advocate descriptor extraction pipeline exists yet, deferred to a future phase",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-07-28T16:34:59.919Z",
    "resolved_at": null
  },
  {
    "id": 2,
    "kind": "unrun-verify",
    "phase": "44",
    "file": "app/src/lib/components/ResolveCard.svelte",
    "line": null,
    "description": "Visual check against resolve-speakers-panel.png (Raw Label badge wrap on a synthetic long label, pre-filled combobox visibility, always-present Descriptor cell) deferred to Plan 44-04's checkpoint per 44-02-PLAN.md verification item 5 — structural/grep-based contract tests pass now, but no visual render has been eyeballed yet.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-01T18:19:47.948Z",
    "resolved_at": null
  },
  {
    "id": 3,
    "kind": "unrun-verify",
    "phase": "47",
    "file": "tests/test_pytest_isolation_invocation_shapes.py",
    "line": null,
    "description": "Task 3's verify command (pytest tests/test_pytest_isolation_invocation_shapes.py) cannot pass until plans 47-02/47-03 land -- api/tests/test_db_isolation_probe.py's autouse _api_lifespan fixture imports api.main -> api.routers.admin, which still imports the retired PipelineRun symbol (47-03's scoped file).",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-08-17T21:03:40.591Z",
    "resolved_at": "2026-08-17T21:30:56.342Z"
  },
  {
    "id": 4,
    "kind": "unrun-verify",
    "phase": "47",
    "file": "tests/test_pytest_isolation_invocation_shapes.py",
    "line": null,
    "description": "bare-testpaths-driven shape still exits non-zero after 47-03 -- full-tree collection hits ImportError: cannot import name 'PipelineRun' in test-body-only references (api/tests/test_admin_dev_routes.py:331, pipeline/tests/test_delete_fixture_argument.py, test_diff_corpus_fixture.py, test_import_convokit_core.py, test_import_convokit_utterances.py), all owned by 47-04/47-05's test-suite conversion, not 47-03's files_modified. The other 2 of 3 parametrized shapes (explicit-single-file, explicit-multi-path) pass cleanly now that 47-03 converted api/routers/admin.py.",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-08-17T21:31:05.797Z",
    "resolved_at": "2026-08-17T22:21:40.026Z"
  },
  {
    "id": 5,
    "kind": "deviation",
    "phase": "47",
    "file": "api/tests/test_phase44_argument_role_roundtrip.py",
    "line": null,
    "description": "Pre-existing SideEnum identity mismatch under bare full-suite pytest -q (testpaths order reimports api.* modules via tests/test_admin_router.py before this file runs) - unrelated to Phase 47 import_run rename, both files predate Phase 47. See deferred-items.md.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-17T22:21:11.348Z",
    "resolved_at": null
  },
  {
    "id": 6,
    "kind": "unmet-truth",
    "phase": "48",
    "file": "api/tests/test_trust_public_leak_ban.py",
    "line": null,
    "description": "test_admin_detail_contract_does_declare_trust_tier fails until plan 48-07 lands trust_tier on ArgumentDetail (D-20); documented as expected/tracked in 48-03-SUMMARY.md, re-run at 48-07 close",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-08-19T13:05:36.138Z",
    "resolved_at": "2026-08-19T15:55:57.028Z"
  },
  {
    "id": 7,
    "kind": "deviation",
    "phase": "48",
    "file": "pipeline/commands/import_convokit.py",
    "line": 515,
    "description": "48-04 Task 1 (Rule 3 blocking-fix) flipped this birth-write status kwarg from PIPELINE to CANDIDATE ahead of plan 48-05's own scheduled edit, to keep the phase 48-04 guard swap internally consistent; 48-05 still owns the rest of this file's birth-logging/recompute scope and will find this one line already done.",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-08-19T14:41:22.505Z",
    "resolved_at": "2026-08-19T15:04:51.300Z"
  },
  {
    "id": 8,
    "kind": "unrun-verify",
    "phase": "48",
    "file": "app/src/routes/admin/arguments/[id]/+page.svelte",
    "line": null,
    "description": "48-08 checkpoint step 8 not executed: no argument with an incomplete resolve step was available, so the non-overridable resolved_at gate (D-14) rendering with NO override field offered is unverified in a browser. Steps 1-7 passed. Re-verify when a resolve-incomplete fixture exists.",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-08-19T23:33:18.102Z",
    "resolved_at": "2026-08-20T16:43:58.653Z"
  },
  {
    "id": 9,
    "kind": "deviation",
    "phase": "48",
    "file": "api/services/admin_arguments.py",
    "line": 448,
    "description": "get_argument_detail's status-log query ordered by created_at first, which can invert insertion order for a writer that reuses a long-lived session/transaction (found live via 48-09's reseed evidence); fixed to order by id ASC in commit 1b7564a78, regression-tested. Underlying stale-created_at STORAGE cause in reset_to_fixture remains open, tracked separately.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-21T14:27:04.542Z",
    "resolved_at": null
  },
  {
    "id": 10,
    "kind": "unmet-truth",
    "phase": "48",
    "file": ".planning/phases/48-trust-lifecycle/48-09-PLAN.md",
    "line": null,
    "description": "Finding 1 (48-EVIDENCE.md): must_haves.truths expected all four corpus fixtures to read trust_tier=trusted after reseed; 15169 and 22372 read uncertain due to ConvoKit's own unattributed-speaker sentinel rows. derive_tier is correct -- the plan's 'corpus mints a Person for every speaker' assumption does not hold universally. Accepted by operator as an open item, not a defect, at the Task 3 checkpoint (2026-08-21).",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-21T14:27:06.606Z",
    "resolved_at": null
  },
  {
    "id": 11,
    "kind": "deviation",
    "phase": "49",
    "file": "api/services/admin_jobs.py",
    "line": null,
    "description": "resolve_job/update_resolve_row_for_job never stamp ArgumentParticipant.source/method; 49-01's D-18 change now floors these to UNCERTAIN. 2 test failures in api/tests/test_admin_jobs_service.py, out of 49-02 scope — see .planning/phases/49-review-model/deferred-items.md",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-08-23T12:43:33.463Z",
    "resolved_at": "2026-08-23T14:10:35.664Z"
  },
  {
    "id": 12,
    "kind": "deviation",
    "phase": "49",
    "file": "api/services/admin_review.py",
    "line": null,
    "description": "_argument_attention_predicate had only 3 legs (needs_review, unresolved_participant, degraded_tier) -- no leg for 'a constituent has an open value_discrepancy', even though _person_attention_predicate already had the equivalent leg for people. Found live during 49-06's own D-32 walkthrough: an operator-edited, already-resolved participant that a lower-authority re-import disagreed with was invisible in /admin/review. Fixed same-plan: leg 4 added, list_review_queue_arguments' constituent-inclusion check widened to match, 2 new regression tests.",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-08-23T16:11:33.813Z",
    "resolved_at": "2026-08-23T16:11:33.813Z"
  },
  {
    "id": 13,
    "kind": "deviation",
    "phase": "49",
    "file": ".planning/phases/49-review-model/49-RESEARCH.md",
    "line": null,
    "description": "Pitfall 4's premise ('no live corpus path can produce an unresolved speaker because _resolve_person always resolves-or-creates') is false -- verified against the live dev DB before 49-06 started: argument 1788 had 11 person_id-IS-NULL participants from a job parked pre-resolve. The dev-only seeder (D-33a) was built anyway, justified instead by its own standalone value (a deterministic, repeatable fixture for 26-UAT/14-UAT), not by the false claim. It WAS initially restated in the shipped docstring of api/services/admin_dev.py::seed_unresolved_speaker_fixture despite the SUMMARY claiming otherwise; the orchestrator corrected that docstring on 2026-08-23.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-23T16:13:01.505Z",
    "resolved_at": null
  },
  {
    "id": 14,
    "kind": "unrun-verify",
    "phase": "49",
    "file": "app/src/routes/admin/review/+page.svelte",
    "line": null,
    "description": "49-01's Confirm-vs-Resolve-speaker-link conditional rendering (tracer feedback gate defect 2 fix) has not been re-verified in a live browser since the fix -- unit/integration-tested only. See 49-01-SUMMARY.md coverage D6.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-23T16:13:12.844Z",
    "resolved_at": null
  },
  {
    "id": 15,
    "kind": "unrun-verify",
    "phase": "49",
    "file": "app/src/lib/components/CreatePersonPopover.svelte",
    "line": null,
    "description": "49-03's CreatePersonPopover Bench/Advocate side-inheritance walkthrough (toggle row to Bench, open Create-new-bench-person, confirm Bench pre-selected, create person, confirm Resolved As shows the name; repeat on Advocate) was never run in a browser -- credential-access denial. See 49-03-SUMMARY.md coverage D1/D2.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-23T16:13:13.173Z",
    "resolved_at": null
  },
  {
    "id": 16,
    "kind": "unrun-verify",
    "phase": "49",
    "file": "app/src/routes/admin/help/+page.svelte",
    "line": null,
    "description": "49-03's /admin/help visual + apolitical read-through (badge colors, 375px width, no ranking language) was never run in a browser -- credential-access denial. See 49-03-SUMMARY.md coverage D4.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-23T16:13:13.491Z",
    "resolved_at": null
  },
  {
    "id": 17,
    "kind": "unrun-verify",
    "phase": "49",
    "file": "app/src/routes/admin/review/+page.svelte",
    "line": null,
    "description": "49-05's Task 2 seven-item browser walkthrough of the full /admin/review screen (tabs, filter composition/back-button/active-filter-indicator, expand/collapse incl. zero-constituent fallback, Confirm/Confirm-as-unattributable/Re-flag actions with D-26 stay-visible behavior, five dashboard StatCards in one row, StatCard singular/zero-state text, no horizontal scroll at 375px) was never run in a browser -- credential-access denial. See 49-05-SUMMARY.md coverage D4/D5.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-23T16:13:13.738Z",
    "resolved_at": null
  },
  {
    "id": 18,
    "kind": "unrun-verify",
    "phase": "49",
    "file": "app/src/routes/admin/arguments/[id]/+page.svelte",
    "line": null,
    "description": "26-UAT Test 26 (unresolved-advocate placeholder + Save gate) -- 49-06's seeder makes the underlying side=UNKNOWN/person_id=NULL data state reachable and script/API-confirmed live on the dev DB, but the actual on-screen render (placeholder text, Save-button disabled state) was never observed in a browser -- credential-access denial. See 26-UAT.md Test 26's phase_49_06_update.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-23T16:19:41.333Z",
    "resolved_at": null
  },
  {
    "id": 19,
    "kind": "unrun-verify",
    "phase": "49",
    "file": "app/src/lib/components/ChatBubble.svelte",
    "line": null,
    "description": "14-UAT Test 8 (non-resolved-utterance avatar) -- 49-06's seeder now also nulls the matching Utterance.person_id rows, script/API-confirmed live on the dev DB, but the argument must also be PUBLISHED to reach the public chat page (a step this seeder deliberately does not perform) and the actual on-screen non-interactive-avatar render was never observed -- credential-access denial. See 14-UAT.md Test 8's phase_49_06_update.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-23T16:19:41.608Z",
    "resolved_at": null
  },
  {
    "id": 20,
    "kind": "unrun-verify",
    "phase": "49",
    "file": "app/src/routes/admin/review/+page.svelte",
    "line": null,
    "description": "D-32's live authority-conflict walkthrough -- fully verified end-to-end via a repeatable script against the live dev DB (operator edit survives, corpus re-import rejected+recorded, discrepancy visible via the API, reflag closes it) in 49-EVIDENCE.md, including finding and fixing a real gap (WINDOWS #12). The actual browser rendering (Discrepancy badge color/placement, click behavior) was never observed -- credential-access denial.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-23T16:19:41.894Z",
    "resolved_at": null
  },
  {
    "id": 21,
    "kind": "unrun-verify",
    "phase": "49",
    "file": "app/src/routes/admin/+page.svelte",
    "line": null,
    "description": "The new 'Seed unresolved speaker' Dev Tools button and its success line were never observed in a browser -- credential-access denial. Backend endpoint and the form action's error-mapping are fully tested; only the button's rendering/behavior is unconfirmed.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-23T16:19:42.185Z",
    "resolved_at": null
  },
  {
    "id": 22,
    "kind": "unrun-verify",
    "phase": "49",
    "file": "app/src/lib/components/CreatePersonPopover.svelte",
    "line": null,
    "description": "WR-01 browser walkthrough (49-09 Task 1 human-check) NOT OBSERVED — sandbox denied .env access for ADMIN_USERNAME/ADMIN_PASSWORD/SESSION_SECRET",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-24T20:00:45.872Z",
    "resolved_at": null
  },
  {
    "id": 23,
    "kind": "unrun-verify",
    "phase": "49",
    "file": "app/src/routes/admin/arguments/[id]/+page.svelte",
    "line": null,
    "description": "Speakers-card published-lock visual verification (49-09 Task 3 human-check) NOT OBSERVED — sandbox denied .env access for ADMIN_USERNAME/ADMIN_PASSWORD/SESSION_SECRET",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-24T20:00:46.273Z",
    "resolved_at": null
  },
  {
    "id": 24,
    "kind": "unrun-verify",
    "phase": "49",
    "file": "api/tests/test_phase49_participant_side_contract.py",
    "line": null,
    "description": "Task 1 human-check (Resolve-card regression walk: toggle behavior, person-clear on real boundary crossing, unchanged labels) not observed in this session — browser tooling unavailable to executor",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-24T22:49:21.712Z",
    "resolved_at": null
  },
  {
    "id": 25,
    "kind": "unrun-verify",
    "phase": "49",
    "file": "app/src/routes/admin/arguments/[id]/+page.svelte",
    "line": null,
    "description": "Task 3 six-item Speakers-card convergence human-check walk not observed in this session — browser tooling unavailable to executor",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-24T22:49:22.058Z",
    "resolved_at": null
  },
  {
    "id": 26,
    "kind": "deviation",
    "phase": "49",
    "file": "app/src/routes/admin/arguments/+page.svelte",
    "line": null,
    "description": "New finding during 49-12 (G-49-5c) live measurement: /admin/arguments overflows at 375px (scrollWidth 680 vs clientWidth 375) via an unwrapped <table> with no overflow-x container -- separate, pre-existing cause independent of AdminSubNav; out of scope for 49-12 (files_modified did not include this page). Not fixed.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-25T10:54:02.125Z",
    "resolved_at": null
  },
  {
    "id": 27,
    "kind": "deviation",
    "phase": "49",
    "file": "app/src/routes/admin/people/+page.svelte",
    "line": null,
    "description": "New finding during 49-12 (G-49-5c) live measurement: /admin/people overflows at 375px (scrollWidth 403 vs clientWidth 375) via an unwrapped <table> with no overflow-x container -- separate, pre-existing cause independent of AdminSubNav. Was previously masked by AdminSubNav's larger 423px overflow (both pegged the page at the same scrollWidth); only became independently visible after 49-12 fixed the sub-nav. Out of scope for 49-12 (files_modified did not include this page). Not fixed.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-25T10:54:09.338Z",
    "resolved_at": null
  },
  {
    "id": 28,
    "kind": "unrun-verify",
    "phase": "49",
    "file": "app/src/routes/admin/arguments/[id]/+page.svelte",
    "line": null,
    "description": "Task 3 browser human-check (5 items) not observed — no browser tool available to the executor; see 49-11-SUMMARY.md Human-Check Items section",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-25T11:18:44.159Z",
    "resolved_at": null
  },
  {
    "id": 29,
    "kind": "deviation",
    "phase": "50",
    "file": "pipeline/commands/import_convokit.py",
    "line": 636,
    "description": "_reconcile_conversation's compare-and-write body is deferred to plan 50-05 by design (50-01-PLAN.md Task 3 scope); it currently only establishes the digest-compare branch and writes nothing on a real content mismatch.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-26T13:51:01.301Z",
    "resolved_at": null
  },
  {
    "id": 30,
    "kind": "unrun-verify",
    "phase": "50-unified-import-path",
    "file": "app/src/routes/admin/review/+page.svelte",
    "line": null,
    "description": "50-04 Task 2 human-check walkthrough not performed: Approve on a candidate corpus argument, tab/filter survival on redirect, Approve button absence post-transition, publish-after-approve, and no-truncation of a discrepancy value at 1280px and narrow viewports — no browser tool / .env admin credential access available to this executor (same constraint as 49-01/49-03/49-05/49-06).",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-26T15:35:23.632Z",
    "resolved_at": null
  }
]
````
