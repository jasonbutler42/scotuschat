---
schema_version: 1
open_count: 4
waived_count: 0
fixed_count: 3
total_count: 7
last_updated: 2026-08-19T15:04:51.300Z
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
| 6 | 48 | unmet-truth | api/tests/test_trust_public_leak_ban.py |  | test_admin_detail_contract_does_declare_trust_tier fails until plan 48-07 lands trust_tier on ArgumentDetail (D-20); documented as expected/tracked in 48-03-SUMMARY.md, re-run at 48-07 close | open |  | 2026-08-19T13:05:36.138Z |  |
| 7 | 48 | deviation | pipeline/commands/import_convokit.py | 515 | 48-04 Task 1 (Rule 3 blocking-fix) flipped this birth-write status kwarg from PIPELINE to CANDIDATE ahead of plan 48-05's own scheduled edit, to keep the phase 48-04 guard swap internally consistent; 48-05 still owns the rest of this file's birth-logging/recompute scope and will find this one line already done. | fixed |  | 2026-08-19T14:41:22.505Z | 2026-08-19T15:04:51.300Z |

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
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-19T13:05:36.138Z",
    "resolved_at": null
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
  }
]
````
