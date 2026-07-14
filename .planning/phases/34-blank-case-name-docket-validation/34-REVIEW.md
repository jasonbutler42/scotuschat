---
phase: 34-blank-case-name-docket-validation
reviewed: 2026-07-14T19:07:24Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - app/tests/case-required-recovery.browser.test.mjs
  - app/src/routes/admin/arguments/[id]/+page.svelte
  - api/tests/test_question_number_nullable.py
findings:
  critical: 0
  warning: 1
  info: 0
  total: 1
status: issues_found
---

# Phase 34: Code Review Report

**Reviewed:** 2026-07-14T19:07:24Z
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Plan 34-04 resolves the previous CR-01: the constraint-valid `use:enhance` callback now clears both native-only flags synchronously before saving, while the later `update()` result remains the owner of structured server-required state. The authenticated Edge/CDP regression exercises the actual invalid-event, correction, server-required, collision, and generic-failure lifecycle, so the previous WR-01 source-only coverage concern is also resolved. Exact copy/order, attempted values, ARIA state, borders, and established collision/generic rendering remain intact.

One test-harness robustness warning remains. The spawned Vite and browser processes are cleaned up on ordinary assertion failures, but their startup errors and premature exits are not observed directly, weakening the fail-closed cleanup guarantee under damaged or permission-blocked installations.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: Subprocess startup failures are not observed and can bypass deterministic cleanup

**File:** `app/tests/case-required-recovery.browser.test.mjs:180-211`

**Issue:** Both `spawn(...)` calls are created without an `error` listener or an early-exit promise. `browserExecutable()` verifies only that a path exists, not that the executable can launch. If Edge exists but is blocked, corrupt, or denied by policy, Node emits an `error` event on the child process; without a listener this becomes an uncaught asynchronous error rather than a controlled test failure. Likewise, if Vite or Edge exits before becoming ready, the harness waits for the full HTTP/CDP timeout instead of reporting the subprocess failure. Depending on how the test runner handles that uncaught event, the callback's `finally` cleanup may be delayed or obscured, contrary to the plan's explicit fail-closed process-cleanup requirement.

**Fix:** Attach `error` and `exit` observers immediately after each spawn, race readiness against a startup-failure promise, and include the executable/process exit details in the rejection. Keep the existing `finally` block as the single cleanup owner. For example, use a helper that returns `{ child, failed }`, where `failed` rejects on `error` or on `exit` before readiness, then `await Promise.race([waitFor(...), failed])` for Vite and Edge/CDP startup.

## Resolved Prior Findings

- **Prior CR-01 resolved:** `app/src/routes/admin/arguments/[id]/+page.svelte:150-151` clears both native-only flags before `savingState`, preventing corrected submissions from inheriting stale required copy, borders, ARIA state, or focus behavior.
- **Prior WR-01 resolved:** `app/tests/case-required-recovery.browser.test.mjs` now drives the actual authenticated Svelte component lifecycle in a real browser; `api/tests/test_question_number_nullable.py` is appropriately supplemental rather than the sole evidence.

---

_Reviewed: 2026-07-14T19:07:24Z_
_Reviewer: Codex (gsd-code-reviewer)_
_Depth: standard_
