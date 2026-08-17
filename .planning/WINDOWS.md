---
schema_version: 1
open_count: 3
waived_count: 0
fixed_count: 0
total_count: 3
last_updated: 2026-08-17T21:03:40.591Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 39 | stub | app/src/lib/components/SpeakerPopover.svelte |  | Advocate descriptor slot renders literal 'Coming soon' — intentional per D-16/39-UI-SPEC.md; no per-advocate descriptor extraction pipeline exists yet, deferred to a future phase | open |  | 2026-07-28T16:34:59.919Z |  |
| 2 | 44 | unrun-verify | app/src/lib/components/ResolveCard.svelte |  | Visual check against resolve-speakers-panel.png (Raw Label badge wrap on a synthetic long label, pre-filled combobox visibility, always-present Descriptor cell) deferred to Plan 44-04's checkpoint per 44-02-PLAN.md verification item 5 — structural/grep-based contract tests pass now, but no visual render has been eyeballed yet. | open |  | 2026-08-01T18:19:47.948Z |  |
| 3 | 47 | unrun-verify | tests/test_pytest_isolation_invocation_shapes.py |  | Task 3's verify command (pytest tests/test_pytest_isolation_invocation_shapes.py) cannot pass until plans 47-02/47-03 land -- api/tests/test_db_isolation_probe.py's autouse _api_lifespan fixture imports api.main -> api.routers.admin, which still imports the retired PipelineRun symbol (47-03's scoped file). | open |  | 2026-08-17T21:03:40.591Z |  |

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
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-17T21:03:40.591Z",
    "resolved_at": null
  }
]
````
