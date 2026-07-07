---
status: diagnosed
trigger: "Resolve card has no visible trigger to create or switch a person on the pipeline job detail page (/admin/pipeline/[job_id]), so the CR-01 regression check (side persistence after create-new-person) could not even be started."
created: 2026-07-07T00:00:00Z
updated: 2026-07-07T00:10:00Z
---

## Current Focus

reasoning_checkpoint:
  hypothesis: "The Resolve card's ENTIRE discrepancy-resolution UI (Confirm/Select/Change buttons, CreatePersonPopover trigger, and the 'Continue Resolve' footer button) is gated behind `isPaused = (jobStatus === 'paused')` in ResolveCard.svelte. The job/run the tester viewed had job.status = 'completed' (not 'paused') because pipeline/commands/resolve.py sets status straight to COMPLETED (never PAUSED) whenever the alias-matching resolve step produces zero misses (all speaker labels auto-resolved). In that state every isPaused-gated branch renders nothing — matching the tester's 'no trigger at all' report — and this is correct, intentional behavior, not a broken trigger."
  confirming_evidence:
    - "ResolveCard.svelte line 72: `let isPaused = $derived(jobStatus === 'paused');` — single source of truth for all discrepancy-resolution UI."
    - "ResolveCard.svelte line 399 (Resolved-as column) and line 650 (Action column) both require `isPaused` before rendering any Confirm/Select/Change/CreatePersonPopover control; when false, they render only static text or '—'."
    - "ResolveCard.svelte line 688: `{#if isPaused && allDispositioned}` gates the 'Continue Resolve' footer button — same isPaused flag."
    - "25-UAT.md Test 2 (same session) reports 'I don't see anything like this' for the Continue Resolve button — a DIFFERENT control gated by the SAME isPaused flag. Two independently-coded controls failing identically is strong evidence of one shared upstream cause (isPaused=false), not two separate broken triggers."
    - "pipeline/commands/resolve.py lines 328-335 and 379-399: when `misses` (unresolvable speaker labels) is empty, admin_jobs.status is set directly to COMPLETED and discrepancies is written but the PAUSED branch (lines 304-373, which is the ONLY place status becomes 'paused') is skipped entirely. A transcript where every speaker auto-resolves via existing aliases never passes through 'paused'."
    - "RunStatusCard.svelte BADGE_LABEL: paused -> 'Needs review', completed -> 'Completed' — these are visibly distinct badges, consistent with the tested job showing a 'Completed'-type badge rather than 'Needs review'."
    - "Commit 64c43139 (Task 3 CSS fix) only changed inline min-height from 32px to 36px on CreatePersonPopover's trigger and ResolveCard row controls — a sizing tweak, not a display/visibility change — ruling out the CSS-fix-broke-the-button hypothesis."
  falsification_test: "If the job actually under test had job.status === 'paused' at the time of UAT (confirmable via `SELECT status FROM admin_jobs WHERE id = <tested_job_id>` or via the RunStatusCard badge reading 'Needs review' in a screenshot), this hypothesis is false and a real isPaused-computation bug (e.g., liveJob not syncing, prop name mismatch) must be sought instead."
  fix_rationale: "N/A — find_root_cause_only mode. No fix applied. Root cause is a state-dependent design (confirmed working as coded) combined with a test/verification-process gap: there was no guaranteed way for the tester to land on a 'paused-with-miss' job, and no in-UI messaging explaining why the row-action UI is absent for a non-paused run."
  blind_spots: "Could not query the live database/admin_jobs table for the actual job.status of the job the tester viewed (worktree has no DB access and is on a stale git ref). Root cause is inferred from strong converging code evidence (two independently-gated controls failing together) plus the resolve.py state-machine, not from direct runtime observation of the exact tested job's status value. If, contrary to available evidence, the tested job actually was 'paused', a different bug in isPaused computation would need to be investigated (e.g. liveJob sync timing, discrepancies always empty even while paused)."

hypothesis: "CONFIRMED — isPaused=false (job likely 'completed') suppresses the entire discrepancy-resolution UI by design; not a broken trigger."
test: "Read ResolveCard.svelte in full (Action/Resolved-as column gating), CreatePersonPopover.svelte, pipeline/commands/resolve.py (paused vs completed branch), +page.svelte (jobStatus wiring), and 25-UAT.md Test 2 for corroboration."
expecting: "n/a — investigation complete for find_root_cause_only mode"
next_action: "Return ROOT CAUSE FOUND to caller; no fix in this mode."

## Symptoms

expected: The just-created person's Bench/Advocate side is NOT reverted — it persists as chosen in the popover. (Exercises code-review fix dc8ad284 / CR-01, which threaded `side` through `handlePersonCreated`/`pendingSideOverrides` in ResolveCard.svelte and calls `submitRow()` immediately.) To even test this, a user must be able to open a "Create new person" popover (or a person-switch affordance) from a Resolve card row.
actual: "Looks like there's no trigger on the resolve card to create or even switch people" — the human tester could not find any button/control on the Resolve card to open the CreatePersonPopover or otherwise select/switch a person for a row.
errors: None reported
reproduction: Test 1 in .planning/phases/25-pipeline-job-detail-page/25-UAT.md — open a pipeline job's detail page at /admin/pipeline/[job_id] where the Resolve card is rendered, look at an intervention row (no auto-match) or any row, and look for a way to create/switch the person.
started: Discovered during UAT of Phase 25 (pipeline-job-detail-page), 2026-07-07.

## Eliminated

- hypothesis: "Genuine rendering regression — CreatePersonPopover trigger button conditionally fails to render even while paused (bad condition, missing prop, or hidden by the Task 3 36px min-height CSS fix in 64c43139)."
  evidence: "Commit 64c43139 diff only changes inline `min-height` from 32px to 36px on ResolveCard row controls and CreatePersonPopover's Popover.Trigger — a sizing-only change, no display/visibility/opacity/conditional-wrapper change. ResolveCard.svelte's conditional chain (isPaused && row.discrepancy && !gated && s.correcting) is logically sound and CreatePersonPopover is unconditionally rendered inside that branch with no additional disabling prop passed from ResolveCard. Also, this hypothesis alone cannot explain Test 2's identical failure (Continue Resolve button missing), since that button shares no code path with CreatePersonPopover — only the isPaused flag."
  timestamp: "2026-07-07"

- hypothesis: "jobStatus prop delivers an unexpected/mismatched value to ResolveCard (e.g., enum serializes uppercase 'PAUSED', or liveJob fails to sync with data.job), causing isPaused to be false even when the backend job really is paused."
  evidence: "AdminJobStatus(str, enum.Enum) in api/models/models.py defines PAUSED = \"paused\" (lowercase); Pydantic v2 model AdminJobResponse.status: AdminJobStatus serializes to the lowercase value with no casing transform anywhere in admin_jobs.py or the polling +server.ts passthrough. app/src/routes/admin/pipeline/[job_id]/+page.svelte wires `jobStatus={liveJob.status}` directly, and `let liveJob = $state(data.job); $effect(() => { liveJob = data.job; });` correctly re-syncs liveJob to fresh load data on every load-function re-run (e.g. initial page load). No prop-name mismatch or transform bug found."
  timestamp: "2026-07-07"

## Evidence

- timestamp: "2026-07-07"
  checked: "app/src/lib/components/ResolveCard.svelte (full file, 733 lines)"
  found: "`isPaused = $derived(jobStatus === 'paused')` (line 72) gates: (a) the entire interactive branch of the 'Resolved as' column (line 399, combobox + CreatePersonPopover only appear when isPaused && row.discrepancy && !gated && s.correcting), (b) the entire 'Action' column's Confirm/Select/Change buttons (line 650: `{#if !isPaused || !row.discrepancy || gated}` renders only '—'), and (c) the 'Continue Resolve' footer button (line 688: `{#if isPaused && allDispositioned}`). When isPaused is false, NONE of these render — the row shows only static read-only text via the personDisplay snippet and a bare '—' in the Action column."
  implication: "There is exactly one flag controlling visibility of ALL discrepancy/person-matching UI in this component. If a tester sees zero triggers anywhere in the table (not just the Create-person popover, but also Confirm/Select/Change and Continue Resolve), the single most likely explanation is isPaused === false for the entire render, not a narrow bug in one control."

- timestamp: "2026-07-07"
  checked: "app/src/lib/components/CreatePersonPopover.svelte (full file, 247 lines)"
  found: "The popover's own trigger (bits-ui Popover.Trigger, 'Create new person') has no independent visibility gate beyond the `disabled` prop (defaults to false, never passed as true from ResolveCard's call site at lines 526-531). The trigger is only ever mounted in the DOM at all when ResolveCard's parent conditional (isPaused && row.discrepancy && !gated && s.correcting) is true — i.e., CreatePersonPopover itself has no bug; it is simply never instantiated outside that branch."
  implication: "Confirms the missing-trigger symptom originates upstream in ResolveCard's conditional gating, not inside CreatePersonPopover."

- timestamp: "2026-07-07"
  checked: "pipeline/commands/resolve.py lines 280-399 (resolve step outcome handling)"
  found: "job.status is set to AdminJobStatus.PAUSED ONLY inside the `if misses:` branch (line 304, DB write at line 358-373) — i.e., only when at least one raw_speaker_label could not be auto-matched via existing alias data. When `misses` is empty (every speaker label auto-resolved), the code takes the `else` branch (line 328) and, for job-driven runs, writes admin_jobs.status = COMPLETED directly (lines 379-399) — PAUSED is never set. discrepancies JSONB is written in both branches, but only the PAUSED branch leaves job.status such that ResolveCard's isPaused is true."
  implication: "A pipeline job whose speakers were all successfully auto-resolved (common for re-runs, or transcripts where every advocate/justice already has a seeded alias) skips 'paused' entirely and lands on 'completed' — the exact state where ResolveCard shows zero interactive discrepancy-resolution controls by design. This is the most probable state of the job the UAT tester was viewing."

- timestamp: "2026-07-07"
  checked: ".planning/phases/25-pipeline-job-detail-page/25-UAT.md Test 1 and Test 2 results (same UAT session)"
  found: "Test 1 (create/switch person trigger): 'Looks like there's no trigger on the resolve card to create or even switch people.' Test 2 (Continue Resolve with zero discrepancies): 'I don't see anything like this.' Both tests failed in the same session against what is presumably the same or similar job state. Test 4 explicitly states it is blocked because 'the Resolve card has no visible trigger to open Create/Switch Person — see Test 1,' confirming the tester never observed ANY isPaused-gated control, not just the popover."
  implication: "Two independently-implemented controls (CreatePersonPopover trigger nested inside the Resolved-as column vs. the standalone Continue Resolve footer button) both being completely absent, in the same test session, is strong converging evidence that they share one upstream cause: isPaused was false for whatever job was being viewed — rather than two separate, unrelated broken triggers."

- timestamp: "2026-07-07"
  checked: "app/src/lib/components/RunStatusCard.svelte badge labels (lines 28-45)"
  found: "BADGE_LABEL maps paused -> 'Needs review' and completed -> 'Completed' — visually and textually distinct badges rendered elsewhere on the same page."
  implication: "If the tested job's status badge read 'Completed' (green) rather than 'Needs review' (amber), that alone would have been a discoverable signal that the job was not in the reviewable/paused state — but nothing in the UAT report indicates the tester checked or was directed to check this badge, which is itself a discoverability/UAT-setup gap worth flagging even though it is not a code bug."

- timestamp: "2026-07-07"
  checked: "git show --stat 64c43139 (the Task 3 min-height CSS fix mentioned in the investigation context)"
  found: "Diff only touches inline `min-height` values (32px -> 36px) on CreatePersonPopover.svelte's trigger and several ResolveCard.svelte row controls, plus an unrelated heading addition in FailedStepGuidance.svelte. No display/visibility/opacity/z-index changes."
  implication: "Eliminates the CSS-fix-broke-the-trigger hypothesis definitively — this commit could not have hidden any element, only resized it."

## Resolution

root_cause: "ResolveCard.svelte gates ALL discrepancy-resolution UI (the Confirm/Select/Change action buttons, the CreatePersonPopover 'Create new person' trigger nested in the Resolved-as column, and the Continue Resolve footer button) behind a single `isPaused = (jobStatus === 'paused')` flag (line 72, consumed at lines 399, 650, and 688). The job the UAT tester viewed almost certainly had job.status = 'completed' rather than 'paused': pipeline/commands/resolve.py only ever sets admin_jobs.status to PAUSED when the resolve step finds at least one unresolvable speaker label ('misses'); when every speaker auto-resolves via existing alias data (no misses), the job goes straight to COMPLETED and 'paused' is never reached (resolve.py lines 300-399). In the completed state, ResolveCard intentionally renders read-only text and '—' placeholders everywhere a control would otherwise appear — this is the documented, intentional Phase 25 design (person re-matching only while paused), not a broken/missing trigger. This is corroborated by Test 2 in the same UAT session independently reporting the differently-coded 'Continue Resolve' button as equally invisible — a control that shares no implementation with CreatePersonPopover but shares the exact same isPaused gate, which rules out a narrow CreatePersonPopover-specific regression (including the recent 36px CSS min-height fix, confirmed as sizing-only) and points to one shared cause: the tested job was not in 'paused' status at test time."
fix: "None applied — find_root_cause_only mode. Recommended follow-up for whoever picks this up: (1) re-run UAT Test 1/2/4 against a job that is confirmed 'paused' (e.g. by checking the RunStatusCard badge reads 'Needs review', or by using/seeding a transcript containing at least one speaker label with no existing alias so resolve.py takes the misses branch); (2) consider adding operator-facing messaging in ResolveCard for the non-paused-but-has-resolveRows case (e.g., 'No pending review — all speakers were auto-resolved' or similar) so operators/testers are not left inferring a missing trigger from a blank Action column; (3) if reproducible against a genuinely paused job, re-open this investigation — that would falsify this root cause and point to a real isPaused-computation bug instead."
verification: ""
files_changed: []
