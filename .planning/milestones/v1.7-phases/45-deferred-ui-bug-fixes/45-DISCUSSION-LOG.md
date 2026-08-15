# Phase 45: Deferred UI Bug Fixes - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-11
**Phase:** 45-Deferred UI Bug Fixes
**Areas discussed:** BUG-01 direct-access response, BUG-01 gate scope, BUG-02 scrollbar fix approach

---

## BUG-01: Direct access response

| Option | Description | Selected |
|--------|-------------|----------|
| 404 Not Found | Argument detail route returns a plain 404, identical to a nonexistent ID — no signal to an unauthenticated visitor that an unpublished argument exists | ✓ |
| Explicit "not published" state | A distinct page/response telling the visitor this argument exists but isn't published yet | |

**User's choice:** 404 Not Found
**Notes:** Chosen to avoid leaking the existence of unpublished content to anyone probing argument IDs.

---

## BUG-01: Gate scope

| Option | Description | Selected |
|--------|-------------|----------|
| Both endpoints | Gate `/arguments/{id}/utterances` AND `/arguments/{id}/speakers` | ✓ |
| Utterances endpoint only | Gate only the primary utterances call | |

**User's choice:** Both endpoints
**Notes:** Ensures no unpublished argument data leaks through either call, even if called independently of normal navigation order.

---

## BUG-02: Scrollbar fix approach

| Option | Description | Selected |
|--------|-------------|----------|
| Move visual card styling onto Popover.Content | Structural fix per diagnosed root cause: put background/border/border-radius on the actual scrolling element | ✓ |
| Also add custom scrollbar styling | Structural fix plus custom `::-webkit-scrollbar`/`scrollbar-color` theming | |

**User's choice:** Move visual card styling onto Popover.Content
**Notes:** Structural fix alone was judged sufficient; custom scrollbar theming left as an option to revisit during implementation only if the structural fix still looks jarring.

---

## Claude's Discretion

- Exact FastAPI mechanism for the 404 (inline `HTTPException` vs. service returning `None`).
- Whether any additional client-side gating is needed beyond the existing `error(res.status, ...)` handling in `+page.server.ts`.

## Deferred Ideas

- Create-person popover side-inheritance/auto-select todo (`2026-08-11-create-person-popover-side-and-selection.md`) — matched by keyword search but out of Phase 45's scope (not BUG-01 or BUG-02); left pending for a future phase.
