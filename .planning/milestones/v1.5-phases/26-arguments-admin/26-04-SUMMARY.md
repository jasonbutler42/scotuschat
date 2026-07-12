---
phase: 26-arguments-admin
plan: 04
subsystem: ui
tags: [sveltekit, svelte5, forms, admin]

# Dependency graph
requires:
  - phase: 26-arguments-admin (Plan 02)
    provides: status_log and speakers arrays on ArgumentDetail; advocate title writable via updateParticipantSide
  - phase: 26-arguments-admin (Plan 01)
    provides: Three-state Argument lifecycle (draft/published/unpublished) and status-keyed delete/publish guards
provides:
  - Rebuilt argument edit page with a Status card (Created/Published dates), status-driven Publish/Unpublish placement, and a timestamped Status history card
  - Unified Speakers section (single table) replacing the Advocate Roles card and tenure-gap-warning banners — advocate role+title+extracted-hint+inline-save, read-only bench rows with tenure-derived role or missing-tenure + Edit person link
  - Draft-only delete gate (can_delete === 'draft') with updated blocked-state tooltip copy
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Publish/Unpublish rendered inside the Status card body (not as a floating standalone block) — status-driven three-way branch (draft/unpublished -> Publish, published -> Unpublish)"
    - "Speakers table renders one <tr> per ArgumentParticipant; advocate rows collapse Role+Title+Save into a single <td colspan=3> containing one independent use:enhance form, matching the existing per-row inline-save convention from the old Advocate Roles card"

key-files:
  created: []
  modified:
    - app/src/routes/admin/arguments/[id]/+page.server.ts
    - app/src/routes/admin/arguments/[id]/+page.svelte

key-decisions:
  - "can_delete changed from `status !== 'published'` to `status === 'draft'` — the client-side gate now matches Plan 26-01's backend gate exactly (Published AND Unpublished both blocked)"
  - "Publish/Unpublish moved from a standalone un-carded block between the old Advocate Roles card and Danger Zone into the Status card body, per the UI-SPEC's layout-simplification note"
  - "Status history rendered as its own card directly below Status (not a sub-section within it) — UI-SPEC left this to planner discretion; a separate card keeps the Status card's badge/dates/publish-control focused and the history list independently scrollable-length"
  - "The Advocate Roles card's per-row form pattern (one <form use:enhance> per row, savingXId state) was extended rather than replaced — Speakers rows reuse this convention for the advocate Role+Title+Save form"

requirements-completed: [AEDIT-01, AEDIT-02, AEDIT-05, AEDIT-06, AEDIT-07, AEDIT-08, AEDIT-09]

coverage:
  - id: D1
    description: "Status card shows the three-state badge, a 'Created {date}' line (relabeled from 'Resolved'), and a 'Published {date}' line when set"
    requirement: "AEDIT-01"
    verification:
      - kind: automated_ui
        ref: "cd app && npm run check (0 errors); grep confirms 'Created ' label and no remaining 'Resolved ' label"
        status: pass
    human_judgment: false
  - id: D2
    description: "Status history card lists every status_log entry oldest-first as {badge} — {date, time}, with the first draft entry labelled 'Created' and a degraded 'Status history is unavailable.' fallback"
    requirement: "AEDIT-02"
    verification:
      - kind: automated_ui
        ref: "cd app && npm run check (0 errors); grep confirms 'Status history' heading and formatDateTime usage"
        status: pass
    human_judgment: false
  - id: D3
    description: "Publish button shows for Draft and Unpublished arguments; Unpublish shows for Published; both live inside the Status card, not floating between Speakers and Danger Zone"
    requirement: "AEDIT-08"
    verification:
      - kind: automated_ui
        ref: "cd app && npm run check (0 errors); grep confirms the old 'resolved_at && !published_at' condition no longer appears"
        status: pass
    human_judgment: false
  - id: D4
    description: "Unified Speakers section: advocate rows get a three-option role select (PETITIONER/RESPONDENT/AMICUS, no UNKNOWN), a title input with an Extracted hint, an utterance count, and inline Save; bench rows show tenure-derived role or Missing tenure + Edit person, each with an utterance count"
    requirement: "AEDIT-05, AEDIT-06, AEDIT-07"
    verification:
      - kind: automated_ui
        ref: "cd app && npm run check (0 errors); grep confirms the Speakers heading, savingSpeakerId state, three-option select, title input, Extracted hint, bench Missing-tenure branch, and utterance_count on every row; old 'Advocate Roles' heading and tenure-gap banner text are gone"
        status: pass
    human_judgment: false
  - id: D5
    description: "Delete is enabled only for Draft arguments; Published and Unpublished show the disabled button with the updated tooltip copy"
    requirement: "AEDIT-09"
    verification:
      - kind: automated_ui
        ref: "app/src/routes/admin/arguments/[id]/+page.server.ts can_delete = argument.status === 'draft'; grep confirms 'Only drafts can be removed.' tooltip copy and old 'Unpublish first.' copy is gone"
        status: pass
    human_judgment: false
  - id: D6
    description: "Full page renders correctly with a live backend argument in each of the three lifecycle states (draft, published, unpublished) — visual/interaction confirmation"
    human_judgment: true
    rationale: "svelte-check and grep verify markup/logic correctness but cannot confirm visual layout, spacing, or actual browser rendering against a running FastAPI backend with real data — requires human UAT per the phase verification note"

duration: 12min
completed: 2026-07-08
status: complete
---

# Phase 26 Plan 04: Argument edit page rebuild Summary

**Rebuilt the `/admin/arguments/[id]` edit page around the three-state lifecycle: Status card with Created/Published dates and in-card Publish/Unpublish, a new timestamped Status history card, a unified Speakers section replacing the old Advocate Roles card and tenure-gap banners, and a Draft-only delete gate.**

## Performance

- **Duration:** ~12 min
- **Tasks:** 3 completed
- **Files modified:** 2

## Accomplishments
- `ArgumentDetail` TS type on the server load now carries `status_log` and a new `SpeakerRow`-typed `speakers` array, mirroring the Plan 26-02 backend schema field-for-field
- `can_delete` now keys on `status === 'draft'`, closing the gap where Unpublished arguments were previously (incorrectly) deletable client-side
- `updateParticipantSide` posts `title` alongside `side`, and the delete-blocked 409 copy matches the UI-SPEC's new Draft-only messaging
- Status card relabeled "Resolved" to "Created" and now hosts the Publish/Unpublish control directly (status-driven: draft/unpublished → Publish, published → Unpublish) instead of a floating button block
- New Status history card renders every `status_log` entry oldest-first as `{badge} — {date, time}`, special-casing the first `draft` entry as "Created", with a degraded-state fallback message
- The old Advocate Roles card and the tenure-gap-warning banner block are both removed and replaced by a single Speakers table (Name | Role | Title | Utterances | Action) covering every participant — advocates get an editable three-option role select, title input with an Extracted hint, and inline Save; bench rows are read-only with tenure-derived role or a Missing-tenure warning + Edit person link
- Danger Zone tooltip copy updated to reflect that both Published and Unpublished arguments are blocked from deletion

## Task Commits

Each task was committed atomically:

1. **Task 1: Edit page server — types, can_delete gate, title-aware save, delete copy** - `4f8a02e1` (feat)
2. **Task 2: Edit page — three-state badge, Status card + history, Publish/Unpublish placement, Danger Zone copy** - `cb910355` (feat)
3. **Task 3: Edit page — unified Speakers section replacing Advocate Roles card and tenure-gap banners** - `94f2068a` (feat)

## Files Created/Modified
- `app/src/routes/admin/arguments/[id]/+page.server.ts` - `StatusLogEntry`/`SpeakerRow` TS types, `status_log`/`speakers` on `ArgumentDetail`, `can_delete === 'draft'`, `title` read/posted in `updateParticipantSide`, updated delete 409 copy
- `app/src/routes/admin/arguments/[id]/+page.svelte` - `unpublished` badge branch, `formatDateTime` helper, in-card Publish/Unpublish, new Status history card, unified Speakers table replacing Advocate Roles + tenure-gap banners, updated Danger Zone tooltip copy

## Decisions Made
- Status history was built as its own card (not a sub-section nested inside the Status card) — the UI-SPEC left this to planner discretion, and a separate card keeps the Status card's primary controls (badge, dates, publish action) visually distinct from the potentially-long history list
- The Speakers table's advocate row uses a single `<td colspan="3">` containing one flex-wrapped form (select + title + hint + count + save) rather than three separate `<td>` cells each with their own form fragment, since the whole row must submit as one `use:enhance` form per D-04
- Kept the `participants` and `tenure_gap_warnings` fields in the server-side `ArgumentDetail` TS type for backward compatibility even though the template no longer reads them, matching the plan's explicit instruction

## Deviations from Plan

None - plan executed exactly as written. All acceptance criteria (SpeakerRow/status_log types, can_delete gate, title-aware save, delete copy, badge branches, Status card relabel, Status history card, publish/unpublish placement, Danger Zone copy, Speakers heading/subheading, three-option select, title input + Extracted hint, bench Missing-tenure + Edit person, utterance counts on every row, old heading/banner text removed) verified via grep and `npm run check` after each task.

## Issues Encountered

None. `cd app && npm run check` reported 0 errors after every task; the pre-existing 17 warnings across 8 files are unrelated to this plan's files (DocketPillInput, ArgumentDetailsCard, ChatBubble, ResolveCard, SpeakerPopover, admin/login, admin/people/[id], admin/pipeline/[job_id]).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 26 (arguments-admin) is now fully implemented across all 4 plans: three-state lifecycle backend (26-01), speakers/status-log data contract (26-02), list page three-state UI (26-03), and this edit page rebuild (26-04). No blockers identified. Remaining work is human UAT against a running backend with real arguments in each of the three lifecycle states (draft, published, unpublished), per the phase verification note — svelte-check and static grep checks cannot substitute for that.

---
*Phase: 26-arguments-admin*
*Completed: 2026-07-08*

## Self-Check: PASSED

All modified files verified present on disk (`+page.server.ts`, `+page.svelte`, this SUMMARY.md); all task and summary commit hashes (4f8a02e1, cb910355, 94f2068a, a173c917) verified present in git log.
