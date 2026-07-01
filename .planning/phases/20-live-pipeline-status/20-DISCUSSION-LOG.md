# Phase 20: Live Pipeline Status - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-01
**Phase:** 20-live-pipeline-status
**Areas discussed:** List page interval, Poll stop conditions, Detail page scope

---

## List Page Interval

| Option | Description | Selected |
|--------|-------------|----------|
| 2.5s | Matches fire-and-poll cadence from Phase 7; less aggressive for list-level updates | |
| 1s — match the detail page | Consistent with detail page; simpler; effectively real-time | ✓ |
| 5s | Conservative, minimizes SSR load function re-runs | |

**User's choice:** 1s for both pages
**Notes:** User asked about 50ms — whether server compute was the only concern. Clarified that the real harm at aggressive intervals is visual DOM churn and form state disruption from `invalidateAll()` re-renders, not server compute. Since pipeline step transitions happen every 10–60 seconds minimum, 50ms offers no perceptible benefit. User agreed 1s is effectively real-time for single-operator use. Consistency across pages is a plus.

---

## Poll Stop Conditions

| Option | Description | Selected |
|--------|-------------|----------|
| Stop when no job is `running` | Poll only while at least one job has status `running` | ✓ |
| Stop when all are in {completed, failed, paused} | `pending` also keeps polling alive | |
| Stop only when all are {completed, failed} | `paused` keeps polling alive — unnecessary | |

**User's choice:** Stop when no job is `running`
**Notes:** `paused` is stable — won't change without operator action. `pending` is a transient pre-start state. Only `running` meaningfully progresses and warrants active polling.

---

## Detail Page Scope

| Option | Description | Selected |
|--------|-------------|----------|
| List page only — detail is done | Existing 1s $effect already satisfies PIPE-24 | ✓ |
| Detail page needs tuning too | Some behavior needs to change | |

**User's choice:** List page only — detail is done
**Notes:** Existing `$effect` + `setInterval` at 1s + `invalidateAll()` already satisfies PIPE-24. Phase 20 primary deliverable = add list-page polling + verify detail page behavior.

---

## Claude's Discretion

None — all three areas were decided by the user.

## Deferred Ideas

None raised during discussion.
