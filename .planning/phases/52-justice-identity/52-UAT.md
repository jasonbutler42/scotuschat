---
status: partial
phase: 52-justice-identity
source: [52-VERIFICATION.md]
started: 2026-09-25T16:05:00Z
updated: 2026-09-28T00:00:00Z
---

## Current Test

[testing paused — 1 item outstanding: test 3 (blocked — no pipeline jobs in dev DB)]

## Tests

### 1. Admin person page Identity card — placement and treatment
expected: Open /admin/people/{id} for a corpus-joined justice (non-blank Oyez Speaker ID) and for an advocate or a D-04 justice (Barrett/Jackson). Confirm (1) the two new rows sit between Full Name and the Name Parts inputs; (2) they match the Full Name readout's box/border/padding/text size; (3) the justice shows real values and the other person shows 'Not in corpus' in grey italic in both rows; (4) neither row can be typed into or focused as a form control.
result: pass
note: |
  Passed after three operator-reported defects were fixed in-flight. Recorded here
  because the test did NOT pass on first presentation, and the automated suite could
  not have caught any of the three.
    1. READ-PATH BUG (fix af7d6b384) — get_person_detail() omitted display_name and
       oyez_speaker_id from the dict the router expands into PersonDetail(**p), which
       silently defaults Optional fields to None. Every person rendered "Not in corpus"
       regardless of stored data. The existing test asserted both fields were None for
       a person with NO corpus join, so it could never fail while the bug existed.
       New test test_get_person_returns_the_actual_corpus_values_not_null pins the
       other half and was verified to fail without the fix.
    2. COPY DEFECT (fix 08327b1e3) — the blank display_name state read "Not in corpus",
       which is false for advocates: they ARE corpus speakers and carry an
       oyez_speaker_id. Measured live: 114 people have both fields, 16 (advocates) have
       an id but no display name, 2 (D-04) have neither. 52-UI-SPEC E3/E4's stated
       rationale — "both fields are blank for exactly the same reason" — was false and
       has been corrected in place. Blank display_name now reads "Uses Full Name".
    3. VISUAL (operator design call) — the read-only readouts were byte-identical to the
       editable inputs. Now flat-chrome (transparent fill, 40%-strength border per the
       new Figma Input/disabled variant), with field descriptions moved below the
       control per Input/invalid. Text contrast kept at 11.87:1 rather than the 3.04:1
       a literal opacity:0.4 would have produced on load-bearing data.

### 2. Live reset-to-fixture run — progress line and evidence-based outcomes
expected: Run one real reset against the dev database: open /admin, run Reset to Fixture through its two-step confirm, watch the status line for the whole run, then open the People directory. Optionally kill the FastAPI process mid-reset to observe the partial-reseed message. The status line advances Seeding justices… → Reseeding fixture 1 of 4… → …4 of 4, in place, never leading reality; the Success state renders on completion; the People directory shows the full justice roster; a mid-reset failure shows the evidence-based partial/inconclusive message, not the blanket corruption claim.
result: pass
verified_by: claude, real browser (headless Chromium via Playwright), 2026-09-28, after fix b8f29e054
verification: |
  Three live resets against the dev DB through /admin's two-step confirm:
    - Run A (cold cache, ~11 min): line advanced Seeding justices -> 1..4 of 4 in
      place; still-running notice at 315s with the line above it; 550 polls
      answered, max gap 2.0s (was ~60s frozen). All four fixtures landed in
      their expected end states.
    - Run B (234s, under the abort): Success state rendered with all 4 fixtures.
    - Run C (abort temporarily forced to 30s, reverted): notice at 36s, line kept
      advancing through 4 of 4, then the page left Running and rendered Success
      on its own at 338s — the new post-still-running completion path.
  Not exercised: killing FastAPI mid-reset (optional in the test text).
previously: issue
reported: "I really need to restart my machine so don't do anything else but log that this is the message I'm seeing: Still reseeding. This request stopped listening before the reset finished, but the server is still working — the progress line below is live. Nothing is wrong with the database; wait for it to finish. I don't see any progress line."
severity: major
run: 2 of 2 (second run, after fix a59a67b0f)

  RUN 1 (before a59a67b0f) — FIXED, verified in code but NOT re-verified live:
    Showed RESET_PARTIAL_ERROR ("do not use it until you run Reset to Fixture
    again") over a database that was in fact complete (132 people, all four
    fixtures in their expected end states, verified directly). Cause:
    classifyFixtureStateOutcome read `fixtures` and ignored `progress`, so a
    still-running reset was indistinguishable from a failed one. Fixed by adding
    the `in-progress` outcome, checked BEFORE the fixture comparison; classifier
    extracted to app/src/lib/admin/resetOutcome.js with 6 unit tests
    (app/tests/reset-outcome-classifier.test.mjs), RESET_ABORT_TIMEOUT_MS raised
    180s -> 280s, 52-UI-SPEC amended four outcomes -> five.

  RUN 2 (this report) — OPEN:
    The new still-running notice renders correctly, so the in-progress branch IS
    being reached and the copy is right. But the operator reports NO progress
    line visible beneath it. The notice's own text promises "the progress line
    below is live", so the screen currently contradicts itself — the same class
    of defect as run 1, one layer up.
    NOT INVESTIGATED — operator had to restart. No diagnosis has been performed
    and none of the below is verified; it is a starting point, not a finding.
    Places to look first:
      - app/src/routes/admin/+page.svelte, the use:enhance result handler: the
        still-running branch returns before `resetRunning = false` and before
        stopResetPolling(), so polling SHOULD continue — confirm it actually does.
      - `await update()` in that branch applies the form result; check whether it
        re-renders in a way that drops the {#if resetRunning} block, or whether
        the error and Running blocks are mutually exclusive in the template.
      - pollResetProgress() only writes resetProgressText when the poll returns a
        RECOGNISED step token; a failing poll or an unrecognised token silently
        leaves the last text. If the first poll never succeeded there may be no
        text to show at all.
      - Whether the FastAPI process was still alive to answer
        /admin/dev-fixture-state during the run.

### 3. Admin Resolve card — JH rendering and unresolved-row avatar
expected: Open an admin pipeline job's Resolve card for an argument with a bench row whose person has a name suffix. Confirm the avatar circle shows JH for John Marshall Harlan, II (not the suffix letter JI), and confirm an unresolved row's avatar looks exactly as it did before this change.
result: blocked
blocked_by: other
reason: "blocked"
note: |
  Precondition absent in the dev database, not a code defect: admin_jobs is empty
  (0 rows; only the 4 fixture arguments exist), and the Resolve card renders only
  inside a pipeline job. Harlan II exists as person 2556. Unblocks once a job is
  created for an argument with Harlan II on the bench. The underlying behavior is
  covered by 52-06's browser test and 52-VERIFICATION SC5 (JH/OH/? asserted in a
  real Chromium) — this item is the operator's eye on the admin surface only.

## Summary

total: 3
passed: 2
issues: 0
pending: 0
skipped: 0
blocked: 1

## Gaps

- gap_id: G-52-2
  truth: "The Running state reports per-fixture progress so a multi-minute destructive operation is distinguishable from a hang (D-15)"
  status: resolved
  resolved_by: b8f29e054
  resolved_at: 2026-09-28
  reason: "User reported: I don't see any progress line. The still-running notice renders and states 'the progress line below is live', but no progress line is visible."
  severity: major
  test: 2
  root_cause: "run_import_convokit scanned the 900MB utterances.jsonl with synchronous I/O (measured 59.6s per fixture) on uvicorn's event loop when awaited by reset_to_fixture, so /dev/fixture-state polls went unanswered for the whole reset and the reset overran the 280s abort. Secondary: after a still-running answer the page had no path out of Running; notice copy said 'below' for a line rendered above."
  artifacts:
    - path: "pipeline/commands/import_convokit.py"
      issue: "blocking corpus reads inside an async function"
    - path: "app/src/routes/admin/+page.svelte"
      issue: "poll never transitioned to a terminal state after still-running"
  missing: []
  debug_session: ""
  fix: "b8f29e054 — reads via asyncio.to_thread (test_utterance_scan_does_not_block_the_event_loop, fails without the fix); poll classifies completion via shared resetOutcome.js; copy 'below' -> 'above'"
  live_reverify: passed 2026-09-28 (see test 2 verification)
