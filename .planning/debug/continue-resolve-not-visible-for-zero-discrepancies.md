---
status: resolved
trigger: "Investigate issue: continue-resolve-not-visible-for-zero-discrepancies — The Continue Resolve control (footer action on ResolveCard) is not visible to a human tester on the pipeline job detail page, so the WR-04 regression check (Continue Resolve with zero discrepancies) could not be confirmed."
created: 2026-07-07T00:00:00Z
updated: 2026-07-12T00:00:00Z
goal: find_root_cause_only
resolved_by: "No code fix needed — diagnosis confirmed this is correct, intentional behavior (paused-only UI correctly hidden when jobStatus !== 'paused'), not a defect. Closed at v1.5 milestone completion 2026-07-12 with no further action; re-testing against a genuinely paused job is the only outstanding recommendation, left as a UAT-process note rather than a tracked bug."
---

## Current Focus

hypothesis: CONFIRMED — the tester's job was not in `jobStatus === 'paused'` state at the time of testing (most likely already `completed` with its Argument created, i.e. `readonlyMode === true`). The footer's render gate `{#if isPaused && allDispositioned}` requires `isPaused` first; the WR-04 fix (disc.length===0 -> true) only changes the second half of that AND, so it can never surface the button on a non-paused job. This is the same root cause as the sibling gap (no Create/Switch Person trigger) — both are paused-only UI that is correctly hidden by design because no job in the tester's session was actually paused.
test: Read ResolveCard.svelte in full (render conditions), the WR-04 commit diff (8492f515), 25-UAT.md results for all 4 tests, and +page.svelte/+page.server.ts for how jobStatus/readonlyMode are computed and passed.
expecting: Confirmed — footer and Action-column paused-only UI both gate on `isPaused`; WR-04 diff only touches the `allDispositioned` derived value (still behind `isPaused`), not a separate visibility flag.
next_action: Report ROOT CAUSE FOUND to caller (goal: find_root_cause_only — no fix_and_verify).

## Symptoms

expected: Pause a job whose discrepancies array is empty (or becomes empty after all rows are resolved via inline saveResolveRow edits). "Continue Resolve" is visible in the ResolveCard footer, and clicking it POSTs an empty `matches: []` array and the job moves from `paused` to `completed`. (Exercises code-review fix 8492f515 / WR-04, which changed the `disc.length === 0` branch from false to true so the button renders/works even with zero discrepancies.)
actual: "I don't see anything like this" — the human tester saw no "Continue Resolve" control at all.
errors: None reported
reproduction: Test 2 in .planning/phases/25-pipeline-job-detail-page/25-UAT.md — pause a job, resolve all discrepancy rows via inline edits (or start with a job whose discrepancies array is already empty), and look for a "Continue Resolve" button in the Resolve card footer.
started: Discovered during UAT of Phase 25 (pipeline-job-detail-page), 2026-07-07.

## Eliminated

- hypothesis: "There's a residual bug in the `allDispositioned` computation or the footer's render condition that still hides the button even when discrepancies is empty, despite the WR-04 fix."
  evidence: "ResolveCard.svelte:187-199 shows `allDispositioned` returns `true` when `disc.length === 0` (post-fix), exactly as WR-04 intends. Footer render at line 688 is `{#if isPaused && allDispositioned}` — logically correct: if isPaused is true and discrepancies is empty/null, allDispositioned evaluates true and the button renders. No residual defect in this logic."
  timestamp: 2026-07-07

- hypothesis: "The WR-04 fix only touched the POST/submission logic (matches:[] payload) but never touched the render condition for the button's visibility — a separate condition still controls visibility and was never patched."
  evidence: "git show 8492f515 diff touches only the `allDispositioned` $derived.by block (single line: `if (disc.length === 0) return false;` -> `return true;`). `allDispositioned` IS the exact boolean consumed directly by the footer's `{#if isPaused && allDispositioned}` (line 688) — there is no separate visibility flag. The fix changes visibility and submission-eligibility simultaneously (matchesJson at line 201-211 also derives from the same `discrepancies` array and correctly serializes to `[]` when empty). Hypothesis refuted: the fix's effect is not confined to submission logic; it directly controls render."
  timestamp: 2026-07-07

## Evidence

- timestamp: 2026-07-07
  checked: "app/src/lib/components/ResolveCard.svelte full read (733 lines)"
  found: "Line 72: `let isPaused = $derived(jobStatus === 'paused');`. Line 187-199: `allDispositioned` returns `false` immediately `if (!isPaused)`, before ever inspecting `disc.length`. Line 650 (Action column): `{#if !isPaused || !row.discrepancy || gated}` shows a plain em-dash instead of Confirm/Select/Change buttons whenever `!isPaused`. Line 526-532 (CreatePersonPopover trigger, sibling gap): only reachable inside the `s?.correcting` branch at line 409, itself only reachable when `isPaused && row.discrepancy` (line 399) and not `gated`. Line 688 (Continue Resolve footer): `{#if isPaused && allDispositioned}`."
  implication: "Every paused-only interactive control in ResolveCard — Action-column Confirm/Select/Change buttons, the person-search combobox + CreatePersonPopover trigger (sibling gap), and the footer Continue Resolve button — is gated behind the single boolean `isPaused`. If the job the tester viewed was not literally `jobStatus === 'paused'`, none of these render, regardless of discrepancy count or the WR-04 fix's correctness."

- timestamp: 2026-07-07
  checked: "git show 8492f515 (WR-04 commit diff)"
  found: "Single-file, 5-line diff to ResolveCard.svelte. Only changes `if (disc.length === 0) return false;` to `return true;` inside the `allDispositioned` $derived.by block. No other file touched. No separate visibility flag exists — `allDispositioned` is both the render gate (line 688) and (transitively, via `matchesJson`) the submission payload driver."
  implication: "WR-04 fix is correctly implemented and correctly wired to the button's actual render condition. Confirms the fix itself is not the defect."

- timestamp: 2026-07-07
  checked: ".planning/phases/25-pipeline-job-detail-page/25-UAT.md (all 4 tests + Gaps + out-of-scope feedback)"
  found: "Test 1 (create/switch person trigger) failed with 'no trigger on the resolve card to create or even switch people' — same isPaused gate as Test 2. Test 2 (Continue Resolve) failed with 'I don't see anything like this'. Test 3 was SKIPPED with reason 'User cannot test in current state', plus out-of-scope feedback requesting a new 'Archived' status for 'pipeline runs whose argument has been created and are now read-only, distinct from completed'. Test 4 was BLOCKED citing 'the Resolve card has no visible trigger to open Create/Switch Person — see Test 1'."
  implication: "All four test outcomes in this UAT session are explained by one shared condition: the job(s) the tester was viewing were not in `paused` status. The tester's own out-of-scope feedback (wanting an 'Archived' status for jobs whose argument is already created) strongly suggests they were viewing/toggling between jobs whose Argument already exists — i.e. `readonlyMode === true` / `jobStatus === 'completed'` — never a job paused mid-resolve with unresolved (or now-empty) discrepancies."

- timestamp: 2026-07-07
  checked: "app/src/routes/admin/pipeline/[job_id]/+page.svelte (lines 400-414) and +page.server.ts (readonlyMode computation, line 245-248)"
  found: "ResolveCard renders whenever `data.resolveRows.length > 0` (line 404), independent of job status — so the card itself (table + status card) is visible even on a completed job, matching the tester's Test 3 remark about seeing a 'Resolve' status card immediately above the resolve table card. `jobStatus={liveJob.status}` (line 410) is passed straight through from the live-polled job resource. `readonlyMode = argument != null && argument.status !== 'pipeline'` (page.server.ts:248) — true once the linked Argument has been created, which is also when a job is most commonly no longer 'paused'."
  implication: "Confirms the ResolveCard container is visible in all job states (explaining why the tester saw a card at all, per Test 3 feedback), but its paused-only interactive contents are correctly suppressed once the job is no longer literally `paused`. This is consistent with the tester viewing an already-completed/read-only job rather than a live paused one."

- timestamp: 2026-07-07
  checked: "pipeline/commands/resolve.py (lines 14, 162, 353-364) and api/services/admin_jobs.py (PAUSED transition guards)"
  found: "`status=PAUSED` is set exclusively by the offline pipeline `resolve` step when it finds raw speaker labels it could not auto-match (resolve.py:353-364). There is no operator-facing UI action to force a job into `paused` from the admin pipeline pages themselves — a job only reaches `paused` by actually running the offline resolve pipeline step against a real transcript with match gaps."
  implication: "Reaching a genuinely paused job for UAT requires either an already-paused job left over from a real pipeline run, or manually running `pipeline/commands/resolve.py` against ingested data / seeding a PAUSED AdminJob row directly in the DB. If no such job existed in the tester's environment at UAT time, Tests 1 and 2 were fundamentally untestable through the UI as currently seeded — independent of any ResolveCard code defect."

## Resolution

root_cause: "ResolveCard.svelte correctly implements the WR-04 fix — `allDispositioned` (line 187-199) returns `true` when `discrepancies` is empty/null while paused, and the footer's render condition (`{#if isPaused && allDispositioned}`, line 688) consumes that same value directly, with no separate/stale visibility flag. However, both the footer 'Continue Resolve' button AND the entire paused-only interactive surface of the Action column (Confirm/Select/Change buttons, person combobox, CreatePersonPopover trigger — the sibling UAT gap) are gated behind `isPaused = (jobStatus === 'paused')`. The human tester's UAT session shows all 4 tests failing/skipping/blocking for the same underlying reason (Test 1's 'no trigger to create/switch people', Test 2's 'I don't see anything like this' for Continue Resolve, Test 3's 'cannot test in current state' plus a request for a new 'Archived' status for jobs whose argument already exists, and Test 4 blocked citing Test 1) — consistent with the tester viewing a job that was NOT in `paused` status (most likely an already-completed job with its Argument created, i.e. `readonlyMode === true`). Because `paused` is set exclusively by the offline pipeline `resolve` step finding real match gaps (pipeline/commands/resolve.py:353-364) — there is no in-UI way to force a job into `paused` — Tests 1 and 2 could not have passed unless a genuinely paused AdminJob existed in the tester's environment at UAT time. No code defect was found in ResolveCard.svelte's visibility logic; the root cause is that the tester's test job(s) were not in the required `paused` precondition state, not a flaw in the WR-04 fix or its render wiring."
fix: "N/A — find_root_cause_only mode. No code fix indicated by evidence; recommended next step is to seed/produce a genuinely PAUSED AdminJob (ideally one with zero remaining discrepancies, to directly exercise the WR-04 edge case) and re-run UAT Tests 1, 2, 3, and 4 against it, rather than modifying ResolveCard.svelte further."
verification: ""
files_changed: []
