---
schema_version: 1
open_count: 1
waived_count: 0
fixed_count: 0
total_count: 1
last_updated: 2026-07-28T16:34:59.919Z
---

# Broken Windows Ledger

> Cross-phase defect register. `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 39 | stub | app/src/lib/components/SpeakerPopover.svelte |  | Advocate descriptor slot renders literal 'Coming soon' — intentional per D-16/39-UI-SPEC.md; no per-advocate descriptor extraction pipeline exists yet, deferred to a future phase | open |  | 2026-07-28T16:34:59.919Z |  |

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
  }
]
````
