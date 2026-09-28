---
phase: 52-justice-identity
reviewed: 2026-09-28T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - api/services/admin_people.py
  - api/tests/test_admin_people_schema_readonly.py
  - app/src/lib/admin/resetOutcome.js
  - app/src/routes/admin/+page.server.ts
  - app/src/routes/admin/+page.svelte
  - app/src/routes/admin/people/[id]/+page.svelte
  - app/tests/reset-outcome-classifier.test.mjs
  - pipeline/commands/import_convokit.py
  - pipeline/corpus/loader.py
  - pipeline/tests/test_corpus_loader.py
  - pipeline/tests/test_import_convokit_core.py
findings:
  critical: 0
  warning: 2
  info: 1
  total: 3
status: issues_found
---

# Phase 52: Code Review Report

**Reviewed:** 2026-09-28
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

> This is an **incremental re-review** since commit `4424f07a4`. It supersedes
> the prior `52-REVIEW.md` (preserved in git history) and covers only the
> hunks changed by `git diff 4424f07a4..HEAD` across the 11 files listed
> above, read with surrounding context.

## Summary

The diff since `4424f07a4` does four independent things: (1) moves
`import_convokit.py`'s synchronous corpus reads (`load_cases`, the
utterances.jsonl scan) onto worker threads via `asyncio.to_thread` so
`run_import_convokit` no longer blocks uvicorn's event loop when awaited
from `admin_dev.reset_to_fixture`; (2) adds a regex prefilter to
`stream_utterances_for_conversation_ids` that skips ~85% of JSONL lines
before `json.loads`; (3) reworks the admin dashboard's Reset-to-Fixture
control so a "still running" 503 keeps the page in its Running state and
lets a live poll (`resetOutcome.js`'s `classifyFixtureStateOutcome`) detect
completion and render the correct terminal state; and (4) surfaces
`display_name`/`oyez_speaker_id` on the admin Person detail read path.

Verified directly:
- The `asyncio.to_thread` offload is correct and race-free: the offloaded
  functions (`load_cases`, `_collect_turns_by_conversation`) are pure
  synchronous file I/O with no shared mutable state and no interaction with
  the asyncpg connection pool or the `_reset_progress_lock` asyncio.Lock in
  `admin_dev.py`. `test_utterance_scan_does_not_block_the_event_loop`
  actually proves the non-blocking property (a concurrent ticker's max gap
  is asserted `< 0.25s` against a patched 0.5s-sleeping scan) rather than
  just asserting the call site looks right — ran it locally, passes.
- The regex prefilter (`_CONVERSATION_ID_RE`) is sound for the reasoning
  given in its comment: an escaped literal quote inside a JSON string value
  breaks the unescaped `"conversation_id":` pattern, so a look-alike
  substring inside free text can never falsely match, and a genuine miss
  (any format the pattern doesn't anticipate) always falls through to the
  full `json.loads` parse rather than being trusted. Confirmed by tracing
  the escaping byte-for-byte and by running
  `test_stream_prefilter_matches_only_the_real_conversation_id_key` plus
  the rest of `test_corpus_loader.py` locally — all pass.
- The new Reset-to-Fixture "still running" / poll-driven completion path
  (`resetAwaitingCompletion`, `finishResetFromPoll`, `pollResetProgress`) is
  correctly synchronized: every state mutation that matters for avoiding a
  double-finish (`resetAwaitingCompletion = false`, `stopResetPolling()`)
  happens synchronously as the first statement of the function that owns
  it, before any `await`, so two overlapping `setInterval` ticks cannot both
  observe the flag as `true` and both call `finishResetFromPoll`. The
  backend's `_clear_reset_progress()` only fires once, in `reset_to_fixture`'s
  `finally` block, so "progress is null" is a reliable last-word signal
  (whether the operation ended in success or in `ResetIncompleteError`) —
  the design correctly delegates "did it actually land" to the fixture-state
  re-read rather than inferring it from "no longer in progress."
- `api/services/admin_people.py`'s two-field addition to
  `get_person_detail` matches `PersonDetail`'s schema (`Optional[str] =
  None` for both), and `display_name`/`oyez_speaker_id` are confirmed
  absent from `PersonUpdate` (which carries `extra="forbid"`), so the new
  `test_admin_people_schema_readonly.py` 422 assertions are testing a real
  contract, not a tautology.

Two warnings below concern a stale-state gap in the Reset-to-Fixture /
seed-unresolved-speaker controls that the new poll-driven completion path
highlights by contrast (it does the state reset correctly; the older,
still-present submit-time and success-path code next to it does not).

## Warnings

### WR-01: Reset-to-Fixture and Seed-unresolved-speaker success paths never clear a prior `form` error, so a stale failure message can render under a fresh success

**File:** `app/src/routes/admin/+page.svelte:580-596` (Reset-to-Fixture), `app/src/routes/admin/+page.svelte:711-726` (Seed unresolved speaker)

**Issue:** Both controls' `use:enhance` callbacks only call `update()` /
`applyAction()` on their failure branch; the success branch sets the local
`$state` result variable and calls `invalidateAll()` directly, never
touching `form`:

```js
if (result.type === 'success' && result.data && Array.isArray(...)) {
  resetResult = (result.data as { resetFixtures: ResetFixtureItem[] }).resetFixtures;
  resetConfirming = false;
  await invalidateAll();          // <-- form is NOT reset here
} else {
  resetResult = null;
  resetConfirming = false;
  await update();                 // <-- only the failure branch clears/sets form
}
```

`invalidateAll()` only reruns `load`; it does not clear the sticky `form`
prop SvelteKit populates from the last action result (`applyAction`/`update`
is the only thing that changes it, which is exactly why the failure branch
calls `update()`). Reproduction: trigger a reset that fails (network error,
non-4-fixture body, etc.) so `form.resetError` is set and rendered via
`{#if form?.resetError}` (line 692); then trigger a second reset that
succeeds. `resetResult` renders the new "✓ Reset complete" badge and
fixture list, but the stale `form.resetError` paragraph from the first
attempt is still rendered directly beneath it, because nothing ever cleared
`form`. The same gap exists for `seedResult`/`form?.seedError` (lines
711-726, rendered at line 755).

The new poll-driven path added in this diff (`finishResetFromPoll`, lines
156-177) gets this right — it calls `applyAction({...})` unconditionally on
both its success and failure branches, which is exactly the established
project convention elsewhere (e.g.
`app/src/routes/admin/people/[id]/+page.svelte:353-357` calls `await
update()` unconditionally regardless of result type). The older code paths
sitting right next to the new one do not follow that convention.

**Fix:** Call `update()` (or `applyAction({type:'success', status:200,
data:{}})`) unconditionally in both success branches, mirroring
`finishResetFromPoll` and the rest of the codebase's convention:

```js
if (result.type === 'success' && result.data && Array.isArray(...)) {
  resetResult = (result.data as { resetFixtures: ResetFixtureItem[] }).resetFixtures;
  resetConfirming = false;
  await update();
  await invalidateAll();
} else {
  ...
}
```

### WR-02: `resetResult` (and `seedResult`) from a prior successful run is not cleared when a new attempt starts, so a stale success badge/list can render underneath the new Running spinner

**File:** `app/src/routes/admin/+page.svelte:560-565` (submit-time reset), `app/src/routes/admin/+page.svelte:710` (seed submit)

**Issue:** The `use:enhance` factory function that fires at submission time
resets `resetRunning`, `resetAwaitingCompletion`, and `resetProgressText`,
but never clears `resetResult`:

```js
use:enhance={() => {
  resetRunning = true;
  resetAwaitingCompletion = false;
  resetProgressText = RESET_PROGRESS_STEP_1_COPY;
  stopResetPolling();
  resetPollHandle = setInterval(pollResetProgress, 1000);
  return async ({ result, update }) => { ... };
}}
```

`resetResult` is rendered unconditionally whenever truthy (`{#if
resetResult}` at line 663), independent of `resetRunning`/`resetConfirming`.
So: run a reset to success (badge + fixture list render), then start a
second reset. While the second run is in its Running (spinner) state — or,
per WR-01's scenario, if the second run also lands in the "still running"
503 branch — the first run's "✓ Reset complete" badge and fixture list are
still visible below the spinner, because nothing cleared `resetResult` at
submission time. An operator could plausibly read the still-visible badge
as confirmation the *new* click already finished. The same gap applies to
`seedResult` at the seed form's submission point (line 710).

**Fix:** Clear the result state when a new submission starts:

```js
use:enhance={() => {
  resetRunning = true;
  resetResult = null;
  resetAwaitingCompletion = false;
  ...
}}
```

and similarly `seedResult = null;` alongside `seedSubmitting = true;`.

## Info

### IN-01: `test_utterance_scan_does_not_block_the_event_loop`'s 0.25s threshold is timing-based and could be flaky under a heavily loaded CI runner

**File:** `pipeline/tests/test_import_convokit_core.py:1516-1561`

**Issue:** The test patches the scan to `time.sleep(0.5)` and asserts a
concurrent asyncio ticker's max observed gap is `< 0.25s`. This correctly
proves the regression it targets (a synchronous 0.5s call on the event loop
would produce a ~0.5s gap, comfortably failing the 0.25s bound), and margin
is generous relative to the 0.5s stimulus. Under a sufficiently
oversubscribed CI host, non-deterministic scheduling delays on the
`asyncio.sleep(0.01)` ticker could in principle push the gap over 0.25s
without the offload actually regressing. Not a defect in the logic being
tested — flagged only as a maintenance note in case this test is ever seen
to flake.

**Fix:** No action needed unless it's observed to flake in practice; if it
does, widening the threshold (e.g. to 0.35-0.4s) preserves a comfortable
margin below the 0.5s stimulus while reducing false failures.

---

_Reviewed: 2026-09-28_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
