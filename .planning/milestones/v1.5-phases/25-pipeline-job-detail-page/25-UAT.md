---
status: complete
phase: 25-pipeline-job-detail-page
source: [25-VERIFICATION.md]
started: 2026-07-07T19:30:58Z
updated: 2026-07-07T20:35:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Create new person via Resolve card popover, then blur Title on same row (CR-01 regression check)
expected: The just-created person's Bench/Advocate side is NOT reverted — it persists as chosen in the popover. (Exercises dc8ad284 / CR-01 fix.)
result: pass
note: "Retest against a genuinely paused job — original 'no trigger' report was caused by testing against a non-paused job (see debug_session on the diagnosed Gap). Inline person creation works; side persists on Title blur. Separately observed (not a fix, captured as a note): the match itself isn't durable until the row is saved — a refresh loses the resolved state, though the created person still appears in the dropdown to re-select."

### 2. Continue Resolve with zero discrepancies (WR-04 regression check)
expected: Pause a job whose discrepancies array is empty (or becomes empty after all rows are resolved via inline saveResolveRow edits). "Continue Resolve" is visible and clicking it POSTs an empty matches:[] array and the job moves from paused to completed. (Exercises 8492f515 / WR-04 fix.)
result: pass
note: "Retest against a genuinely paused job — original report was caused by testing against a non-paused job (see debug_session on the diagnosed Gap). Continue Resolve renders and behaves as coded."

### 3. Full five-state lifecycle walkthrough
expected: Walk a single run through all five lifecycle states end-to-end: not-ready → ready → Create Argument → already-created (read-only), plus a failed run and a paused/resolve run. RunStatusCard shows correct badge/copy/CTA in each state; ArgumentDetailsCard and ResolveCard become read-only exactly once the argument leaves "pipeline" status; FailedStepGuidance shows step-specific copy for Ingest/Parse/Resolve failures; resolve-row side-first gate, per-row saveResolveRow persistence, and Missing-tenure/Edit-person link all behave as coded. Also confirms bench-role recalculation after saving Argument Details (roadmap SC #5) is visible in the resolve card without a manual page reload.
result: pass
note: "Retested after Tests 1/2/4 passed against a genuinely paused job. User signed off: 'All testing passes' — meets the phase's agreed requirements, though user has follow-up UX ideas for the Resolve table already captured separately (SEED-001, the cosmetic spacing gap below, and the 2026-07-07-phase-25-uat-retest.md note)."

### 4. Mobile/responsive check on Resolve card and CreatePersonPopover
expected: On a narrow/mobile viewport, the horizontally-scrollable table wrapper avoids row text overlap; the popover stays within calc(100vw - 32px) and traps/returns focus correctly on open/close.
result: pass
note: "Table portion passed on mobile (no row text overlap). Popover portion retested against a genuinely paused job after the Test 1 precondition issue was resolved — stays within viewport, focus trap/return behaves correctly."

## Summary

total: 4
passed: 4
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "The just-created person's Bench/Advocate side is NOT reverted — it persists as chosen in the popover. (Exercises dc8ad284 / CR-01 fix.)"
  status: resolved
  resolution: "Retested 2026-07-07 against a genuinely paused job (user-confirmed) — PASS. Confirms the diagnosis: original failure was caused by testing against a non-paused job, not a code defect. No code change made."
  reason: "User reported: Looks like there's no trigger on the resolve card to create or even switch people"
  severity: major
  test: 1
  root_cause: "NOT A CODE DEFECT. ResolveCard.svelte gates every discrepancy-resolution control (Confirm/Select/Change buttons, CreatePersonPopover trigger, Continue Resolve footer) behind a single isPaused = (jobStatus === 'paused') flag. The job the tester viewed almost certainly had status 'completed' (its Argument already created), not 'paused' — in that state ResolveCard intentionally renders read-only text/'—' everywhere a control would appear. 'paused' is set exclusively by the offline pipeline resolve step when it finds at least one unresolvable speaker label (pipeline/commands/resolve.py:280-399); when every speaker auto-resolves, the job goes straight to 'completed' and 'paused' is never reached. There is no in-UI way to force a job into 'paused'."
  artifacts:
    - path: "app/src/lib/components/ResolveCard.svelte"
      issue: "All paused-only interactive controls (rows 72, 114-122, 249-258, 399-541, 650-680, 688-731) are correctly gated behind isPaused, but the UI gives no explicit messaging when isPaused is false and the row/table has no pending review, so a tester on a completed job sees a blank/dash Action column indistinguishable from a broken trigger."
    - path: "pipeline/commands/resolve.py"
      issue: "Lines 280-399: job reaches COMPLETED directly (bypassing PAUSED) whenever the resolve step has zero misses — determines whether the reviewable UI is ever reachable for a given job."
  missing:
    - "A genuinely PAUSED AdminJob to re-test Test 1 against (seed a transcript with a speaker label lacking an existing alias so resolve.py takes the misses branch)."
    - "Optional: operator-facing messaging in ResolveCard for the 'no pending review / all auto-resolved' case so a blank Action column doesn't read as a missing/broken trigger."
  debug_session: ".planning/debug/resolve-card-missing-create-switch-person-trigger.md"

- truth: "\"Continue Resolve\" is visible and clicking it POSTs an empty matches:[] array and the job moves from paused to completed. (Exercises 8492f515 / WR-04 fix.)"
  status: resolved
  resolution: "Retested 2026-07-07 against a genuinely paused job (user-confirmed) — PASS. Confirms the diagnosis: original failure was caused by testing against a non-paused job, not a code defect. No code change made."
  reason: "User reported: I don't see anything like this"
  severity: major
  test: 2
  root_cause: "NOT A CODE DEFECT — same root cause as Test 1's gap. The WR-04 fix is correctly implemented: allDispositioned (ResolveCard.svelte:187-199) returns true when discrepancies is empty/null, and the footer's render condition ({#if isPaused && allDispositioned}, line 688) consumes that same value directly with no separate/stale visibility flag. But the footer is gated behind isPaused first — if the tester's job was not literally 'paused' (most likely already 'completed' with its Argument created), the button cannot render regardless of discrepancy count. paused is set exclusively by the offline pipeline resolve step finding real match gaps; there is no operator-facing way to force a job into paused from the admin UI."
  artifacts:
    - path: "app/src/lib/components/ResolveCard.svelte"
      issue: "Continue Resolve footer (line 688) correctly implements WR-04 but is unreachable unless isPaused is true."
  missing:
    - "A genuinely PAUSED AdminJob with zero remaining discrepancies to directly exercise the WR-04 edge case and confirm Continue Resolve renders/works."
  debug_session: ".planning/debug/continue-resolve-not-visible-for-zero-discrepancies.md"

- truth: "Resolve card status card and resolve table card render as visually distinct, properly spaced cards."
  status: resolved
  resolution: "Fixed 2026-07-07 (commit c126ef5b): step-cards flex container was missing margin-bottom (only had gap between its own children), and table <th> headers lacked the padding-right: 12px that every <td> already had, causing 'Title'/'Action' headers to visually collide. Both fixed. Separately, user flagged via screenshot that having two sibling 'Resolve' cards at all (pipeline step-status card + resolve-workflow card) is questionable UX, even though it was an intentional Phase 25 decision (D-05/D-20, UI-SPEC Layout Contract). That larger question is deferred to SEED-001 rather than reworked here."
  reason: "User reported: the resolve card html feels malformed: there is a card that says 'resolve' and has the current status. Then, immediately below it with no spacing between them, is another card with the resolve table."
  severity: cosmetic
  test: 3
  artifacts:
    - path: "app/src/routes/admin/pipeline/[job_id]/+page.svelte"
      issue: "Step-cards flex container (line ~235) had gap:16px for its own children but no margin-bottom, so nothing separated it from the sibling ResolveCard below it."
    - path: "app/src/lib/components/ResolveCard.svelte"
      issue: "Table <th> headers (lines 375-380) lacked padding-right: 12px that every <td> body cell already had, so narrow/empty columns (Title, when all visible rows are BENCH) let 'Title' and 'Action' header text visually touch."
  missing: []

## Out-of-scope feedback — both routed and delivered (closed 2026-08-18)

Captured during this phase's UAT as feedback needing a routing decision, not as
failed tests. Both were routed and shipped; recorded here in place of the original
HTML comment, which the cross-phase UAT audit surfaced as two phantom open items
(a commented-out bullet list still parses as `## Gaps`-shaped entries).

- status: resolved
  item: "New pipeline-run status \"Archived\" (grey/neutral) for runs whose argument is created and are now read-only, distinct from \"completed\"."
  resolution: "Delivered in Phase 26. `is_archived` was added to AdminJobResponse and populated via outerjoin in list_jobs(); the badge renders on both the detail page (RunStatusCard) and the list page. Human-verified in 26-UAT.md Test 27 \"Pipeline list page — Archived badge\" — pass."
- status: resolved
  item: "User intends to write up further requirements for reworking the Resolve table as part of this milestone."
  resolution: "Became SEED-001-rework-resolve-table-requirements, promoted to RESOLVE-01-06 and delivered as Phase 44 (Resolve Table Rework) in v1.7. STATE.md records the seed as dormant, its bulk absorbed."


