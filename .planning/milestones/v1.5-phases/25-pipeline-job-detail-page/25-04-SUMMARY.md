---
phase: 25-pipeline-job-detail-page
plan: 04
subsystem: frontend
tags: [sveltekit, svelte5-runes, bits-ui, admin-pipeline, resolve, ui-composition]

# Dependency graph
requires:
  - phase: 25-01
    provides: "RunReadiness/FailedStepRecovery schemas, ResolveRowUpdate schema, PATCH .../resolve-rows mutation, PersonCreate raw_speaker_label/side fields"
  - phase: 25-02
    provides: "ResolveRow schema and GET .../resolve-rows read endpoint (locked column contract)"
  - phase: 25-03
    provides: "+page.server.ts load() returning readiness/failedRecovery/resolveRows/readonlyMode; saveResolveRow/addPerson/saveJobMetadata actions"
provides:
  - "RunStatusCard.svelte — primary run status card (badge, source PDF, Not ready/Ready/Already created states, relocated Create Argument CTA)"
  - "FailedStepGuidance.svelte — step-specific human guidance + raw-error details block, rendered inside the failed step card"
  - "ResolveCard.svelte — locked-column resolve table merging resolveRows with in-flight discrepancy matching, per-row saveResolveRow side/title persistence, side-first gating, Continue Resolve footer"
  - "CreatePersonPopover.svelte — bits-ui Popover mini create-person flow (name + Bench/Advocate) posting to the existing addPerson action"
  - "Final +page.svelte composition: RunStatusCard → ArgumentDetailsCard → step cards → ResolveCard → provenance link → Danger Zone"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cross-cell form submission via HTML form= attribute: ResolveCard renders one hidden <form action=\"?/saveResolveRow\"> per row and references it from a <select>/<input> in separate <td> cells via form=\"resolve-row-form-{id}\", avoiding invalid <form> nesting inside a <table> while still submitting side+title together through requestSubmit()."
    - "Two-source row merge: ResolveCard merges the authoritative resolveRows (side/title/argument_role/bench_role/editable, always available) with the ephemeral discrepancies array (auto-match candidates, only present while job.status === 'paused') by raw_speaker_label, since the two backend contracts serve different lifecycle phases of the same ArgumentParticipant row."
    - "Side-first gating tracked client-side only: sideGateConfirmed/pendingSideOverrides are local $state keyed by participant_id, not derived from any backend 'unset' sentinel (SideEnum has no such value) — gating exists purely to force an explicit Bench/Advocate choice before the person typeahead activates for rows with no auto-match, per D-11/PJOB-18."
    - "CreatePersonPopover and ResolveCard's per-row forms manage their own use:enhance success/failure locally instead of reading the shared page-level `form` prop — avoids ambiguity when multiple independent forms (per-row saves, popovers) could produce results in the same render pass."

key-files:
  created:
    - app/src/lib/components/RunStatusCard.svelte
    - app/src/lib/components/ResolveCard.svelte
    - app/src/lib/components/FailedStepGuidance.svelte
    - app/src/lib/components/CreatePersonPopover.svelte
  modified:
    - app/src/routes/admin/pipeline/[job_id]/+page.svelte

key-decisions:
  - "ResolveCard's 'Bench/Advocate' select is the single write path for both the side column AND the Argument Role column's underlying value — there is no separate 'Argument Role' write field in the backend's ResolveRowUpdate schema (only side/title), so Argument Role is rendered as a read-only derived display (tenure-derived bench_role/missing_tenure for BENCH rows, ADVOCATE_LABEL_MAP-style argument_role for advocate rows) while the actual edit control lives in the Bench/Advocate cell. This satisfies D-14 ('Argument Role... editable before Create Argument') without inventing a field the backend doesn't support."
  - "Person re-matching (Confirm/Select/Create person) only appears while job.status === 'paused', reusing the existing ?/resolve batch-matches action unchanged — Phase 25 does not add a backend path to reassign person_id after the pipeline resolve step commits, so ResolveCard's 'Resolved as' column becomes a plain read-only name+role display once paused/matching state exits, with side/title remaining editable via saveResolveRow independently through Create Argument."
  - "Chose a horizontally-scrollable table wrapper (overflow-x: auto) over UI-SPEC's alternative 'stacked mobile rows' option for the Resolve table — the UI-SPEC and T-25-13 both explicitly list the scrollable wrapper as an acceptable choice ('use a horizontally scrollable table wrapper OR stacked mobile rows'), and it required no new responsive breakpoint logic."
  - "Preserved the existing Danger Zone markup and 'Confirm delete' button text verbatim rather than adding the UI-SPEC Copywriting Contract's 'Destructive confirmation' sentence — CONTEXT D-09/D-22 and this plan's Task 2 action text both explicitly instruct preserving Danger Zone's existing markup/confirmation text unchanged, which supersedes that one UI-SPEC copy row for this phase."
  - "The pipeline step card still labeled 'Resolve' (progress badge) and the new ResolveCard's 'Resolve' heading intentionally coexist as separate sibling cards per the UI-SPEC Layout Contract's explicit sibling-card list — they represent different concepts (pipeline step progress vs. the operator resolve workflow), not a naming collision to fix."

requirements-completed: [PJOB-01, PJOB-02, PJOB-08, PJOB-14, PJOB-15, PJOB-16, PJOB-17, PJOB-18, PJOB-19, PJOB-20, PJOB-21, PJOB-22, PJOB-23]

coverage:
  - id: D1
    description: "RunStatusCard renders the backend-derived not_ready/ready/already_created states with a status badge, source PDF link, blocker checklist, and the relocated Create Argument CTA — no client-side readiness inference (D-01 through D-04, D-18, D-20, D-21, PJOB-01, PJOB-02, PJOB-20)."
    requirement: "PJOB-01"
    verification:
      - kind: unit
        ref: "cd app; npm run check (0 errors)"
        status: pass
    human_judgment: true
    rationale: "Type-checking confirms the component consumes Plan 25-03's readiness/pdfHref contract correctly, but no browser-driven or DB-backed manual pass exercised the three readiness states, the approve form's redirect-to-readonly transition, or the badge's live-polling interaction in this environment (no DATABASE_URL configured) — needs manual UAT against /admin/pipeline/[id] before sign-off."
  - id: D2
    description: "ResolveCard renders the locked column order (Raw label, Resolved as, Bench/Advocate, Argument Role, Title, Action), keeps auto-matched rows complete but changeable, gates person selection behind an explicit side choice for intervention rows, hides the Title column for BENCH rows, and persists side/title edits immediately via saveResolveRow (D-10 through D-19, D-21, PJOB-14 through PJOB-18, PJOB-21)."
    requirement: "PJOB-14"
    verification:
      - kind: unit
        ref: "cd app; npm run check (0 errors)"
        status: pass
    human_judgment: true
    rationale: "Type-checking confirms the merged resolveRows/discrepancies data flow and the form=/requestSubmit() cross-cell submission pattern compile correctly, but the paused-state matching flow, the side-first gate, and the saveResolveRow round-trip were not exercised against a running FastAPI + database in this environment — needs manual UAT (start a run through resolve pause, confirm/correct rows, edit side/title, Continue Resolve) before sign-off."
  - id: D3
    description: "CreatePersonPopover captures only name + Bench/Advocate side in a bits-ui Popover (trapped focus, viewport-bounded width, focus returns to trigger on close) and posts to the existing addPerson action, wiring the created person back into the row's candidate list (D-12, D-13, PJOB-19)."
    requirement: "PJOB-19"
    verification:
      - kind: unit
        ref: "cd app; npm run check (0 errors)"
        status: pass
    human_judgment: true
    rationale: "Type-checking and source review confirm the popover's payload shape matches Plan 25-03's addPerson action contract, but the popover was not exercised in a browser (focus trap, viewport-width behavior at mobile breakpoints, actual person creation round-trip) in this environment."
  - id: D4
    description: "FailedStepGuidance shows step-specific human guidance and a 'Start a new run' link to /admin/pipeline first, with the raw technical error inside an expandable <details> block using pre-wrap/break-word — rendered inside the failed step's own card, replacing the old standalone bottom panel and never suggesting same-source rerun (D-05 through D-08, PJOB-08, PJOB-22 supersession)."
    requirement: "PJOB-08"
    verification:
      - kind: unit
        ref: "cd app; npm run check (0 errors)"
        status: pass
    human_judgment: true
    rationale: "Source review confirms guidance/raw_error separation and the removal of any rerun affordance, but a live failed-job render (all three step-specific guidance variants, the details disclosure) was not exercised in a browser in this environment."
  - id: D5
    description: "Final page composition renders RunStatusCard, then ArgumentDetailsCard (readonly-aware), then sibling step cards, then ResolveCard, then a trimmed provenance/participant link, then the unchanged Danger Zone last in every state — with the old floating Create Argument button, Ready-to-publish panel, post-approval rerun flow, bottom error panel, and inline discrepancy table all removed (D-01 through D-22, PJOB-20 through PJOB-23)."
    requirement: "PJOB-23"
    verification:
      - kind: unit
        ref: "cd app; npm run check (0 errors)"
        status: pass
      - kind: unit
        ref: ".venv/Scripts/python.exe -m pytest api/tests/test_admin_jobs_phase25.py api/tests/test_admin_people_phase25.py -q (30 passed, 24 skipped — unaffected baseline)"
        status: pass
    human_judgment: true
    rationale: "Source-level audit against every D-01 through D-22 decision and every Phase 25 PJOB requirement found no missing item (see Deviations/Task 3 notes below for the two gaps found and fixed), but full visual/interaction verification (not-ready, ready, failed, paused-resolve, already-created states; mobile table overflow; focus outlines) requires a browser and a seeded database, neither available in this environment."

duration: ~55min
completed: 2026-07-07
status: complete
---

# Phase 25 Plan 04: Job Detail Card Composition Summary

**Four new Svelte 5 components (RunStatusCard, ResolveCard, FailedStepGuidance, CreatePersonPopover) plus a full `+page.svelte` recomposition that turns `/admin/pipeline/[id]` into a sibling-card operator workflow — run status first, resolve fully restructured with locked columns and side-first gating, failed recovery contextual to its step card, and Danger Zone unchanged and last.**

## Performance

- **Duration:** ~55 min
- **Tasks:** 3 completed (Task 3 found and fixed 2 minor gaps in Task 1's components rather than requiring `+page.svelte` changes)
- **Files created:** 4 (`RunStatusCard.svelte`, `ResolveCard.svelte`, `FailedStepGuidance.svelte`, `CreatePersonPopover.svelte`)
- **Files modified:** 1 (`app/src/routes/admin/pipeline/[job_id]/+page.svelte` — 1012 lines removed, 53 lines added in the composition change, net page size dropped by ~950 lines as the discrepancy table, advocate dropdowns, rerun flow, and error panel moved into the new components)

## Accomplishments

- **RunStatusCard** — the first workflow card after the page header. Renders a text-labeled status badge (job status, not readiness), the source PDF link, and one of three backend-derived states: `not_ready` (blocker checklist, no CTA), `ready` (`Create Argument` form posting to the existing `?/approve` action), or `already_created` (`Argument created` copy + `Open argument editor` link, no rerun). Supersedes the old floating Create Argument button and the old "Ready to publish"/post-approval rerun panels entirely.
- **ResolveCard** — the restructured Resolve workflow. Merges Plan 25-02's `resolveRows` (authoritative side/title/argument_role/bench_role/missing_tenure/editable) with the job's in-flight `discrepancies` (auto-match candidates, present only while `status === 'paused'`) keyed by `raw_speaker_label`. Renders the locked column order (Raw label, Resolved as, Bench/Advocate, Argument Role, Title, Action); Title is hidden entirely for BENCH rows. Side and title edits submit immediately per-row via `?/saveResolveRow` using a hidden per-row `<form>` referenced by HTML `form=` attributes from controls in separate `<td>` cells (avoids invalid `<form>`-inside-`<table>` nesting). Rows needing intervention (no auto-match) require an explicit Bench/Advocate choice before the person typeahead activates (D-11/PJOB-18); auto-matched rows skip this gate. `Continue Resolve` lives in the card footer, shown only when every discrepancy row is dispositioned.
- **FailedStepGuidance** — renders inside the failed step's own card (not a standalone bottom panel). Shows a "This run failed" heading, the backend's step-specific human guidance first (`role="alert"`), a "Start a new run" link to `/admin/pipeline`, and the raw technical error inside a `<details>` block with `pre-wrap`/`break-word` styling. Never offers same-source rerun.
- **CreatePersonPopover** — a `bits-ui` `Popover` mini create-person flow (name + Bench/Advocate toggle only), width-bounded for mobile (`min(420px, calc(100vw - 32px))`), posting to the existing `?/addPerson` action and reporting the created person back to the calling row via an `onCreated` callback.
- **Page composition** — `+page.svelte` now renders: header → `RunStatusCard` → `ArgumentDetailsCard` (readonly-aware, unchanged component) → sibling step cards (parse stats and the ingest PDF link preserved; `FailedStepGuidance` rendered inside whichever step card is failed) → `ResolveCard` (only when the argument has participant rows) → a trimmed provenance/participant-count link (full per-row detail now lives in ResolveCard, so the old advocate-side dropdown listing was dropped to avoid duplicated/stale state) → the unchanged Danger Zone, last in every state.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Phase 25 card components** — `c8d73789` (feat)
2. **Task 2: Compose the job detail page and relocate actions** — `1088717e` (feat)
3. **Task 3: Verify source coverage and visual interaction states** — `64c43139` (fix) — audit found 2 gaps in Task 1's components (see Deviations) rather than requiring `+page.svelte` changes

_Note: `tdd_mode` is `false` in `.planning/config.json`; all tasks were implemented and verified with `npm run check` per commit rather than as separate RED/GREEN commits._

## Files Created/Modified

- `app/src/lib/components/RunStatusCard.svelte` — Primary run status card; badge, PDF link, three readiness states, relocated Create Argument CTA.
- `app/src/lib/components/ResolveCard.svelte` — Locked-column resolve table; merges resolveRows + discrepancies; per-row saveResolveRow persistence; side-first gating; Continue Resolve footer.
- `app/src/lib/components/FailedStepGuidance.svelte` — Step-specific failed guidance + raw-error details block.
- `app/src/lib/components/CreatePersonPopover.svelte` — bits-ui Popover mini create-person flow.
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` — Recomposed around the four new cards; removed the old floating Create Argument button, Ready-to-publish panel, post-approval rerun confirm flow, bottom failed-error panel, inline discrepancy review table, and advocate-side dropdown participant listing.

## Decisions Made

See frontmatter `key-decisions` for the full list. Highlights:

- Argument Role has no independent backend write field (only `side`/`title` are writable per `ResolveRowUpdate`), so it is rendered read-only and driven entirely by the Bench/Advocate select's value — this is not a missing feature, it is the correct mapping of the backend contract.
- Person re-matching (Confirm/Select/Create person) only appears while `job.status === 'paused'`, reusing the unchanged `?/resolve` batch action; there is no Phase 25 backend path to reassign `person_id` after that step commits, so post-pause the Resolved-as column becomes a plain read-only display while side/title stay editable via `saveResolveRow`.
- Chose the horizontally-scrollable table wrapper over stacked mobile rows for the Resolve table — both are explicitly sanctioned by the UI-SPEC/T-25-13, and the wrapper needed no new breakpoint logic.
- Preserved Danger Zone's existing markup and "Confirm delete" text verbatim (no new "Destructive confirmation" sentence) per CONTEXT D-09/D-22 and this plan's explicit "preserve unchanged" instruction, which supersedes that one UI-SPEC copy row.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Dense table/action controls under the UI-SPEC's 36px minimum**
- **Found during:** Task 3 source audit against the Accessibility Contract
- **Issue:** `ResolveCard`'s row action buttons (Confirm/Select/Change/Bench/Advocate-gate), the Bench/Advocate select, the Title input, and `CreatePersonPopover`'s trigger button were all built at 32px (copied from the pre-Phase-25 combobox pattern), but the UI-SPEC's Spacing Scale exceptions require "Dense table controls may use 36px minimum height when embedded in rows."
- **Fix:** Raised all affected controls to `min-height: 36px`.
- **Files modified:** `app/src/lib/components/ResolveCard.svelte`, `app/src/lib/components/CreatePersonPopover.svelte`
- **Verification:** `cd app; npm run check` → 0 errors.
- **Committed in:** `64c43139` (Task 3 commit)

**2. [Rule 2 - Missing critical functionality] Missing "This run failed" heading**
- **Found during:** Task 3 source audit against the Copywriting Contract
- **Issue:** The UI-SPEC's Copywriting Contract lists `Failed heading | This run failed`, but `FailedStepGuidance` only rendered the guidance paragraph, omitting the heading present in the old standalone error panel.
- **Fix:** Added an `<h3>This run failed</h3>` heading before the guidance paragraph.
- **Files modified:** `app/src/lib/components/FailedStepGuidance.svelte`
- **Verification:** `cd app; npm run check` → 0 errors.
- **Committed in:** `64c43139` (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (Rule 2 — missing critical functionality, both accessibility/copy compliance gaps caught by the Task 3 audit).
**Impact on plan:** No scope creep — both fixes bring Task 1's components into full compliance with the UI-SPEC contracts Task 1 was already supposed to satisfy; no new features, endpoints, or architectural changes.

## Task 3 Source Audit Results

Reviewed every D-01 through D-22 decision and every Phase 25 PJOB requirement (PJOB-01, 02, 08, 14–23) against the final component/page source. All are represented in code (see `coverage` block above for the itemized mapping). No missing items found beyond the two gaps fixed above.

**Verification unavailable in this environment** (no `DATABASE_URL`, no browser):
- Live rendering of RunStatusCard's three readiness states, the approve-to-readonly transition, and badge polling.
- ResolveCard's paused-state matching flow end-to-end (side-first gate → typeahead → Confirm/Select/Create person → Continue Resolve → job transition).
- CreatePersonPopover's focus-trap/return-focus behavior and mobile viewport width clamping in an actual browser.
- FailedStepGuidance's three step-specific guidance variants against a real failed job.
- Mobile table overflow behavior for the Resolve card's horizontally-scrollable wrapper.

Per Offen's AI Innovation Program stage-gate, this UI work should be manually verified against `/admin/pipeline/[id]` with a seeded database (confirming the not-ready/ready/failed/paused-resolve/already-created states) before any production-facing rollout, consistent with the same caveat carried forward from Plans 25-01 through 25-03.

## Issues Encountered

None beyond the two audit gaps documented above. The pre-existing `a11y_click_events_have_key_events` warning on the resolve combobox's `<li>` options (carried forward unchanged from the pre-Phase-25 implementation's identical pattern) was left as-is per the Scope Boundary rule — it is not a regression introduced by this plan, and reworking the combobox's keyboard model was out of scope for a card-relocation plan.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 25 is now fully implemented end-to-end across all four plans: backend contracts (25-01, 25-02), server bridge (25-03), and UI composition (25-04).
- Before UAT/production sign-off, run a DB-backed manual pass against `/admin/pipeline/[id]` covering all five run states (not-ready, ready, failed, paused-resolve, already-created) — see the `coverage` block above and each plan's own "Next Phase Readiness" note for the specific gaps left by the absence of `DATABASE_URL` in this execution environment.

---

*Phase: 25-pipeline-job-detail-page*
*Completed: 2026-07-07*

## Self-Check: PASSED

All created files exist on disk and all three task commit hashes (`c8d73789`, `1088717e`, `64c43139`) are present in git history.
