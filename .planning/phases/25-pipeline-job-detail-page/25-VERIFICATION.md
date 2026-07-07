---
phase: 25-pipeline-job-detail-page
verified: 2026-07-07T19:21:44Z
status: passed
score: 4/5 truths verified
behavior_unverified: 1
overrides_applied: 0
requirements_checked:

  - PJOB-01
  - PJOB-02
  - PJOB-08
  - PJOB-14
  - PJOB-15
  - PJOB-16
  - PJOB-17
  - PJOB-18
  - PJOB-19
  - PJOB-20
  - PJOB-21
  - PJOB-22
  - PJOB-23

behavior_unverified_items:

  - truth: "Saving Argument Details triggers bench role recalculation visible in the resolve card (roadmap SC #5, D-17, PJOB-17)"
    test: "With a DB-backed environment: open a paused/ready run with a BENCH participant whose current CourtTenure does not cover the existing argued_date (showing 'Missing tenure'), edit Argument Details to a date that IS covered by a tenure, save, and observe the Resolve card's Bench/Advocate Argument Role column without a manual page reload."
    expected: "The bench_role for that row updates from 'Missing tenure' to the tenure-derived seat name without the operator refreshing the page — SvelteKit's use:enhance default update() must actually invalidate the load function and refetch resolveRows with the new argued_date."
    why_human: "This is a runtime state-transition (save → invalidate → refetch → re-render) that static type-checking and source review cannot exercise; no DATABASE_URL is configured in this sandbox so the DB-backed integration test for get_job_readiness/list_resolve_rows_for_job (and the SvelteKit round-trip) could not run — every Phase 25 SUMMARY explicitly flags this as needing a DB-backed/browser pass before sign-off."
human_verification:

  - test: "Create a new person via the Resolve card's 'Create new person' popover on an intervention row (choosing Bench or Advocate), then blur the Title input on that same row immediately after."
    expected: "The just-created person's Bench/Advocate side is NOT reverted — it persists as chosen in the popover. (This exercises the CR-01 code-review fix: dc8ad284 threaded `side` through `handlePersonCreated`/`pendingSideOverrides` and calls `submitRow()` immediately; the fix report itself flags this as 'requires human verification.')"
    why_human: "State-consistency regression across two sequential form submissions (create-person POST, then per-row PATCH) — cannot be exercised without a running FastAPI + database + browser."

  - test: "Pause a job whose discrepancies array is empty (or becomes empty after all rows are resolved via inline saveResolveRow edits instead of the batch discrepancy flow) and confirm 'Continue Resolve' renders and transitions the job to completed."
    expected: "'Continue Resolve' is visible and clicking it POSTs an empty matches:[] array and the job moves from paused to completed. (Exercises the WR-04 fix: 8492f515 changed the `disc.length === 0` branch from false to true; the fix report itself flags this as 'requires human verification.')"
    why_human: "Requires a live paused job with a specific discrepancy-count edge case and a real ?/resolve round trip against the backend — not exercisable via static analysis."

  - test: "Walk a single run through all five lifecycle states end-to-end: not-ready → ready → Create Argument → already-created (read-only), and separately a failed run and a paused/resolve run."
    expected: "RunStatusCard shows the correct badge/copy/CTA in each state; ArgumentDetailsCard and ResolveCard become read-only exactly once the argument leaves 'pipeline' status; FailedStepGuidance shows step-specific copy for Ingest/Parse/Resolve failures; the resolve-row side-first gate, per-row saveResolveRow persistence, and the Missing-tenure/Edit-person link all behave as coded."
    why_human: "No DATABASE_URL is configured in this sandbox, so every DB-backed integration test across all four Phase 25 plans is skipped (30 passed / 24 skipped in the current test run) and no browser is available — this is the single largest verification gap and is explicitly called out in every plan SUMMARY's 'Next Phase Readiness' section as required before production sign-off."

  - test: "Open the Resolve card and CreatePersonPopover on a narrow/mobile viewport."
    expected: "The horizontally-scrollable table wrapper avoids row text overlap; the popover stays within `calc(100vw - 32px)` and traps/returns focus correctly on open/close."
    why_human: "Visual/responsive layout and focus-trap behavior require a real browser viewport; not verifiable from source alone."
gaps: []
deferred: []
---

# Phase 25: Pipeline Job Detail Page Verification Report

**Phase Goal:** The pipeline job detail page at `/admin/pipeline/[id]` has a run status card as the primary status element, a fully restructured resolve card, and all previously floating action buttons moved into contextually appropriate cards.
**Verified:** 2026-07-07T19:21:44Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Run status card shows status badge and source file link and has 3 states: Not ready (lists blockers), Ready ("Create Argument" CTA), Already created (link to argument edit page) | ✓ VERIFIED | `app/src/lib/components/RunStatusCard.svelte:44-181` renders a text-labeled badge, a conditional "View source PDF" link, and switches on `readiness.state` for `not_ready` (blocker `<ul>`, no CTA), `ready` (`?/approve` form, "Create Argument" button), and `already_created` ("Argument created" copy + "Open argument editor" link). Backend `get_job_readiness` (`api/services/admin_jobs.py:601-689`) derives the three states server-side; pure/structural unit tests pass (`test_run_readiness_schema_states`, `test_get_job_readiness_already_created_short_circuits`). DB-backed integration tests for the full derivation are skipped (no `DATABASE_URL` — documented, expected gap). |
| 2 | Failed step card shows the error message and contextual next-step actions including re-run — no standalone floating "Re-run" button exists anywhere on the page | ✓ VERIFIED (documented requirement supersession) | `FailedStepGuidance.svelte` renders inside the failed step's own card (`+page.svelte:390-395`) with a "This run failed" heading, step-specific human guidance (`role="alert"`), a "Start a new run" link to `/admin/pipeline`, and the raw error in a `<details>` block. Confirmed via `grep`: no button anywhere in `+page.svelte`/component tree calls the `?/rerun` action — the old floating Re-run button and post-approval rerun panel are fully removed (WR-01 review fix also removed a dead `participant_side` PATCH block from the `approve` action). The roadmap wording "including re-run" is explicitly and traceably superseded by a locked phase decision (`25-CONTEXT.md` D-05, D-20: "A failed run should not offer `Re-run with same source` as the primary failed-card action") and the approved `25-UI-SPEC.md`'s "Requirement Tension" section, which states this supersession is "an intentional requirement clarification, not a design gap." The literal `?/rerun` action remains defined in `+page.server.ts:335-363` but is unreachable dead code (no caller) — flagged as an info-level cleanup item below, not a functional gap. |
| 3 | Resolve card columns show: Raw label, Resolved as (avatar + name), Bench/Advocate side, Argument Role, Title (advocates only), and Action — no confirmation checkmark column | ✓ VERIFIED | `ResolveCard.svelte:374-381` table header renders exactly this locked column order. Column 2 ("Resolved as") shows an avatar/initials + name via the `personDisplay` snippet (lines 291-322); auto-match/correction states render inline text ("✓ Confirmed" / "✓ Corrected") inside that same cell rather than as a separate checkmark column — confirmed no dedicated confirmation column exists. Column 5 ("Title") is rendered only when `side !== 'BENCH'` (line 619), hidden entirely for bench rows per PJOB-15; backend `ResolveRow.title`/`title_hint` are forced `None` for BENCH rows (`api/services/admin_people.py` bench branch). |
| 4 | Resolve card is fully editable in Not ready and Ready states and read-only in Already created state; bench roles display tenure lookup result or "Missing tenure" when no matching tenure exists | ✓ VERIFIED | `readonlyMode` is computed once in `+page.server.ts:248` (`argument != null && argument.status !== 'pipeline'`) and passed to `ResolveCard` (`interactive = !readonlyMode`) and `ArgumentDetailsCard` (`readonly` prop, which disables inputs and hides the Save button — `ArgumentDetailsCard.svelte:142,183,237`). Server-side, `update_resolve_row_for_job` (`api/services/admin_jobs.py:697-765`) independently rejects any edit once `argument.status != PIPELINE` (defense in depth, not just a UI-layer guard). Tenure lookup: `_bench_role_and_missing_tenure` (`api/services/admin_people.py:564-584`) compares `CourtTenure` date windows against `Argument.argued_date` with no fallback, returning explicit `missing_tenure=True` plus a `person_edit_href`; `ResolveCard.svelte:601-611` renders "Missing tenure" (warning color) + "Edit person" link, or the resolved seat name. Pure-function unit tests for the tenure window predicate pass; DB-backed row-assembly tests are skipped (documented, expected gap). |
| 5 | Saving Argument Details triggers bench role recalculation visible in the resolve card; "Create Argument" and "Continue Resolve" actions live inside their respective cards, not as floating buttons | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED (CTA-placement half is ✓ VERIFIED; recalculation half is unverified) | CTA placement: "Create Argument" lives inside `RunStatusCard`'s `ready` branch (`RunStatusCard.svelte:139-173`); "Continue Resolve" lives in `ResolveCard`'s footer (`ResolveCard.svelte:688-725`), gated on `allDispositioned`. `grep` across `+page.svelte` confirms neither button exists as a standalone/floating element. Bench-role recalculation: `saveJobMetadata` returns `refreshResolveRows: true` (`+page.server.ts:583`) and `ArgumentDetailsCard`'s `use:enhance` handler calls the default `update()` on success (`ArgumentDetailsCard.svelte:75`), which by SvelteKit's default behavior invalidates the load function and refetches `resolveRows` with the new `argued_date`. This is a save → invalidate → refetch → re-render **state transition** that no test exercises — every Phase 25 plan SUMMARY explicitly flags it as needing a DB-backed/browser pass before sign-off. See `behavior_unverified_items` in frontmatter. |

**Score:** 4/5 truths verified, 1 present-behavior-unverified (see frontmatter `behavior_unverified_items`)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `api/schemas/admin_jobs.py` | RunReadiness, ReadinessBlocker, FailedStepRecovery, ResolveRowUpdate, extended PersonCreate | ✓ VERIFIED | All types present; `ResolveRowUpdate.title` carries `max_length=500` (WR-03 fix). |
| `api/services/admin_jobs.py` | get_job_readiness, derive_failed_step_recovery/get_failed_step_recovery, update_resolve_row_for_job, create_person_for_job | ✓ VERIFIED | All present at the lines cited above; guarded transactions, IDOR checks confirmed by source read. Dead duplicate `list_people` removed (WR-05 fix — confirmed absent via grep). |
| `api/routers/admin.py` | GET/PATCH `/jobs/{job_id}/resolve-rows`, GET `/jobs/{job_id}/readiness`, GET `/jobs/{job_id}/failed-recovery`, POST `/jobs/{job_id}/people` | ✓ VERIFIED | All five endpoints present, all inherit router-level `Depends(verify_admin_token)` (line 111), all map service `ValueError` → 422. Module imports cleanly (`python -c "from api.routers import admin"` → OK). No-op `db.commit()` removed from local-upload path (WR-06 fix). |
| `api/schemas/admin_people.py` / `api/services/admin_people.py` | ResolveRow schema, list_resolve_rows_for_job, tenure lookup | ✓ VERIFIED | Present and matches the locked column contract; see truth #4 evidence. |
| `app/src/lib/components/RunStatusCard.svelte` | Primary run status card | ✓ VERIFIED | Exists, substantive (181 lines, three real states), wired into `+page.svelte:213-218`. |
| `app/src/lib/components/ResolveCard.svelte` | Restructured resolve card + footer CTA | ✓ VERIFIED | Exists, substantive (732 lines), wired into `+page.svelte:404-414`. |
| `app/src/lib/components/FailedStepGuidance.svelte` | Failed-step guidance + details disclosure | ✓ VERIFIED | Exists, substantive, wired into each failed step card (`+page.svelte:390-395`). |
| `app/src/lib/components/CreatePersonPopover.svelte` | Mini create-person popover | ✓ VERIFIED | Exists, substantive, wired from `ResolveCard.svelte:526-531`; posts to `?/addPerson`. |
| `app/src/routes/admin/pipeline/[job_id]/+page.svelte` | Final page composition | ✓ VERIFIED | Recomposed: header → RunStatusCard → ArgumentDetailsCard → step cards (with FailedStepGuidance inline) → ResolveCard → provenance link → Danger Zone (last, unchanged). |
| `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` | Server bridge: load + actions | ✓ VERIFIED | `load()` fetches readiness/failedRecovery/resolveRows/readonlyMode with graceful degradation; `saveResolveRow`, extended `addPerson`, `saveJobMetadata` (with `refreshResolveRows`) all present; `ADMIN_TOKEN` never returned to the browser. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `RunStatusCard.svelte` | `+page.server.ts` `?/approve` | `<form action="?/approve">` | ✓ WIRED | Confirmed at `RunStatusCard.svelte:140-141`; server action redirects to the same page on success, re-rendering read-only. |
| `ResolveCard.svelte` | `CreatePersonPopover.svelte` | row action opens mini person form with raw label and side | ✓ WIRED | `ResolveCard.svelte:526-531` passes `rawSpeakerLabel`, `defaultAdvocateSide`, and `onCreated` callback; callback threads `side` through to `pendingSideOverrides` and calls `submitRow()` (CR-01 fix confirmed present at line 249-258). |
| `ResolveCard.svelte` | `+page.server.ts` `?/saveResolveRow` | side/title row edits | ✓ WIRED | Hidden per-row `<form action="?/saveResolveRow">` (line 345-368) referenced via HTML `form=` attribute from the `<select>` (line 564) and `<input>` (line 622) in separate `<td>` cells; action PATCHes `api/admin/jobs/{job_id}/resolve-rows`. |
| `ArgumentDetailsCard.svelte` | `ResolveCard.svelte` refresh | metadata save triggers invalidate/refresh | ⚠️ WIRED, behavior unverified | Code path exists and type-checks (see truth #5 evidence); the actual runtime invalidation → re-render round trip is untested in this environment. |
| `api/routers/admin.py` | `api/services/admin_jobs.py` / `api/services/admin_people.py` | job-scoped admin endpoints call service helpers with `X-Admin-Token` auth | ✓ WIRED | Confirmed via source read of all five new/modified endpoints; router-level auth dependency applies uniformly. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Non-DB backend tests (schema, pure-function, structural) pass | `.venv/Scripts/python.exe -m pytest api/tests/test_admin_jobs_phase25.py api/tests/test_admin_people_phase25.py -q` | `30 passed, 24 skipped in 1.07s` | ✓ PASS |
| Full backend suite has no new regressions | `.venv/Scripts/python.exe -m pytest api/tests -q` | `3 failed, 120 passed, 59 skipped` — the 3 failures are the pre-existing `test_arguments.py`/`test_people.py` lifespan-initialization failures documented in `deferred-items.md`, unrelated to Phase 25 | ✓ PASS (no new regressions) |
| Frontend type-check | `cd app; npm run check` | `COMPLETED 793 FILES 0 ERRORS 17 WARNINGS 8 FILES_WITH_PROBLEMS` | ✓ PASS |
| Router module imports cleanly | `python -c "from api.routers import admin"` | `OK` | ✓ PASS |
| DB-backed integration tests (readiness derivation, resolve-row persistence, tenure lookup end-to-end, endpoint HTTP round trips) | N/A — `DATABASE_URL` not configured in this sandbox | 24 tests skipped via `skipif` | ? SKIP (documented, expected — see `deferred-items.md`) |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|-----------------|--------------|--------|----------|
| PJOB-01 | 25-01, 25-03, 25-04 | Run status card: badge + source file link | ✓ SATISFIED | RunStatusCard.svelte |
| PJOB-02 | 25-01, 25-03, 25-04 | Run status card 3 states | ✓ SATISFIED | RunStatusCard.svelte + get_job_readiness |
| PJOB-08 | 25-01, 25-04 | Failed step card: error + contextual actions | ✓ SATISFIED | FailedStepGuidance.svelte |
| PJOB-14 | 25-01, 25-02, 25-03, 25-04 | Resolve editable/read-only lifecycle | ✓ SATISFIED | readonlyMode + update_resolve_row_for_job guard |
| PJOB-15 | 25-01, 25-02, 25-04 | Locked resolve columns, no checkmark column, Title advocate-only | ✓ SATISFIED | ResolveCard.svelte column order + bench title=null |
| PJOB-16 | 25-02, 25-04 | Bench tenure lookup / Missing tenure | ✓ SATISFIED | `_bench_role_and_missing_tenure` |
| PJOB-17 | 25-03, 25-04 | Metadata save recalculates bench roles | ⚠️ present, behavior unverified | refreshResolveRows flag + default update() invalidation — untested round trip |
| PJOB-18 | 25-01, 25-02, 25-03, 25-04 | Side-first gating before person selection | ✓ SATISFIED | `needsSideGate`/`confirmSide` in ResolveCard.svelte |
| PJOB-19 | 25-01, 25-03, 25-04 | Mini create-person sets is_justice + side | ✓ SATISFIED | create_person_for_job + CreatePersonPopover (CR-01, WR-02 fixes applied) |
| PJOB-20 | 25-01, 25-03, 25-04 | Create Argument in run status card, no floating button | ✓ SATISFIED | RunStatusCard.svelte |
| PJOB-21 | 25-02, 25-04 | Continue Resolve in resolve card footer, no floating button | ✓ SATISFIED | ResolveCard.svelte footer (WR-04 fix applied) |
| PJOB-22 | 25-01, 25-03, 25-04 | Failed recovery avoids standalone rerun | ✓ SATISFIED (documented supersession) | See truth #2 evidence |
| PJOB-23 | 25-04 | Danger Zone unchanged, last | ✓ SATISFIED | +page.svelte:451-508 preserved verbatim |

**No orphaned requirements found.** All 13 Phase 25 requirement IDs from `REQUIREMENTS.md`'s Phase 25 mapping are claimed by at least one plan's `requirements` frontmatter, and every claimed ID is represented in the shipped code.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` | 335-363 | Orphaned `rerun` action — no caller anywhere in `+page.svelte` or its component tree | ℹ️ Info | Dead code, not a functional gap (satisfies "no standalone floating Re-run button"), but a maintenance hazard if a future component re-adds a call to `?/rerun`. Not blocking. |
| `app/src/lib/components/CreatePersonPopover.svelte` | 125, 131 | `id`/`for` built directly from `rawSpeakerLabel` (may contain spaces/punctuation) | ℹ️ Info | Pre-existing REVIEW.md IN-01 finding, explicitly excluded from the review-fix scope; not spec-compliant but tolerated by browsers today. |
| `api/services/admin_people.py` | ~704-712 | `title_hint` sourced from the same column as `title` (no separate "originally extracted" value) | ℹ️ Info | Pre-existing REVIEW.md IN-02 finding, documented as an intentional limitation; the "Extracted:" label can mislead after an edit. Not blocking. |

No debt markers (`TBD`/`FIXME`/`XXX`) or unresolved `TODO`/`HACK`/`PLACEHOLDER` comments found in any Phase 25-modified file. No stub implementations, no empty handlers, no hardcoded-empty data flowing to rendering.

### Code Review Status

`25-REVIEW.md` found 1 critical + 6 warnings + 2 info (9 total). `25-REVIEW-FIX.md` confirms all 7 in-scope findings (critical + warnings) were fixed, with the two info-level findings explicitly excluded from scope (carried forward above as anti-pattern info items, not blockers). All 7 fixes were verified present in the current source during this verification pass:

- CR-01 (side-discard-and-revert bug) — fixed, `ResolveCard.svelte:249-258` — confirmed present, **flagged for human verification** (see `human_verification`).
- WR-01 (dead PATCH block in approve action) — fixed, confirmed removed from `+page.server.ts`.
- WR-02 (orphaned Person on missing side) — fixed, confirmed `ValueError` guard present in `create_person_for_job`.
- WR-03 (unbounded title length) — fixed, confirmed `max_length=500` on `ResolveRowUpdate.title`.
- WR-04 (Continue Resolve stuck on zero discrepancies) — fixed, confirmed `disc.length === 0 → true`, **flagged for human verification** (see `human_verification`).
- WR-05 (dead duplicate `list_people`) — fixed, confirmed absent via grep.
- WR-06 (no-op `db.commit()`) — fixed, confirmed removed.

### Human Verification Required

See frontmatter `human_verification` and `behavior_unverified_items` for the full structured list. In summary, four items need a DB-backed / browser-based pass before production sign-off:

1. **Bench role recalculation after Argument Details save** — the save → invalidate → refetch → re-render round trip (D-17/PJOB-17) is coded but not exercised by any test.
2. **CreatePersonPopover side persistence regression check** — confirms the CR-01 fix actually holds under a real create-then-blur sequence.
3. **Continue Resolve with zero discrepancies** — confirms the WR-04 fix actually renders the button and completes the transition.
4. **Full five-state lifecycle walkthrough + mobile/responsive check** — the single largest gap, explicitly flagged in every Phase 25 plan's SUMMARY, caused by the sandbox having no `DATABASE_URL` and no browser.

### Gaps Summary

No coded gaps found. Every roadmap Success Criterion and every Phase 25 requirement (PJOB-01/02/08/14 through 23) is backed by real, wired, non-stub implementation, confirmed by direct source reads (not SUMMARY.md claims), a clean type-check, clean module imports, and passing non-DB-gated tests. All 7 in-scope code-review findings (1 critical, 6 warnings) were verified fixed in the current source. The one held-back item is a **behavior-unverified truth**, not a failure: the bench-role-recalculation round trip (roadmap SC #5, second half) has correct-looking code on both ends (client invalidation trigger + backend recomputation) but no test — unit, integration, or manual — has ever exercised the full round trip, and the sandbox's lack of `DATABASE_URL`/browser access means this verification pass cannot supply that missing behavioral evidence itself. Two additional review-fix items (CR-01, WR-04) were explicitly self-flagged by the fixer as "requires human verification" and are carried forward here rather than silently marked passed.

This routes the phase to `human_needed` rather than `passed` — not because any success criterion failed, but because the roadmap's own decision tree requires human sign-off whenever unverified runtime-behavior items exist, and this phase currently has four such items, all stemming from the same documented, pre-existing sandbox constraint (no `DATABASE_URL`, no browser) rather than from any code defect found during this review.

---

*Verified: 2026-07-07T19:21:44Z*
*Verifier: Claude (gsd-verifier)*
