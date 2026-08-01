---
schema_version: 1
open_count: 2
waived_count: 0
fixed_count: 0
total_count: 2
last_updated: 2026-08-01T18:19:47.948Z
---

# Broken Windows Ledger

> Cross-phase defect register. `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 39 | stub | app/src/lib/components/SpeakerPopover.svelte |  | Advocate descriptor slot renders literal 'Coming soon' — intentional per D-16/39-UI-SPEC.md; no per-advocate descriptor extraction pipeline exists yet, deferred to a future phase | open |  | 2026-07-28T16:34:59.919Z |  |
| 2 | 44 | unrun-verify | app/src/lib/components/ResolveCard.svelte |  | Visual check against resolve-speakers-panel.png (Raw Label badge wrap on a synthetic long label, pre-filled combobox visibility, always-present Descriptor cell) deferred to Plan 44-04's checkpoint per 44-02-PLAN.md verification item 5 — structural/grep-based contract tests pass now, but no visual render has been eyeballed yet. | open |  | 2026-08-01T18:19:47.948Z |  |

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
  }
]
````
