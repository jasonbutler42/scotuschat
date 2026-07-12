---
phase: 30-corpus-import-resolve-workflow
plan: 03
subsystem: ui
tags: [svelte, sveltekit, admin, pipeline, provenance]

# Dependency graph
requires:
  - phase: 30-corpus-import-resolve-workflow (30-02)
    provides: AdminJobResponse.source field (pdf | corpus) passed through +page.server.ts
provides:
  - Source column on /admin/pipeline/ list table distinguishing corpus-imported jobs from PDF-ingested jobs
affects: [30-04-corpus-import-resolve-workflow]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "sourceLabel()/sourceTagStyle() derived-tag helpers mirroring the existing badgeStyle()/badgeLabel() pattern in the same file"

key-files:
  created: []
  modified:
    - app/src/routes/admin/pipeline/+page.svelte

key-decisions:
  - "Visual verification (Task 2) completed via direct dev-database inspection rather than a live click-through, because the dev DB currently has zero corpus-imported AdminJob rows to display (see Deviations)."

patterns-established:
  - "Provenance tag pattern: quiet, static, non-interactive <span> tag with pre-existing neutral tokens (#94a3b8/#0f1117), kept visually separate from the semantic status badge — reusable for any future job-metadata display columns."

requirements-completed: [PJOB-01]

coverage:
  - id: D1
    description: "Source column (Status | Source | Created | View) renders sourceLabel(job.source) via sourceTagStyle() for every row on /admin/pipeline/"
    requirement: PJOB-01
    verification:
      - kind: automated_ui
        ref: "npx svelte-check --tsconfig ./tsconfig.json --threshold error (0 new errors)"
        status: pass
      - kind: manual_procedural
        ref: "Direct dev-database inspection of admin_jobs rows confirmed PDF-ingested jobs render the 'PDF' tag correctly in the new column; corpus-imported rows are not yet visible in the Pipeline list because they predate 30-01/30-02 and remain unlinked (see Deviations) — column code path confirmed correct, full round-trip visual confirmation deferred to plan 30-04"
        status: pass
    human_judgment: true
    rationale: "Column styling/positioning is a visual judgment call per the UI-SPEC contract; user reviewed the code, the PDF-row rendering, and the explanation for the missing corpus rows, and approved."

# Metrics
duration: 12min
completed: 2026-07-10
status: complete
---

# Phase 30 Plan 03: Pipeline List Source Column Summary

**Quiet neutral "PDF"/"Corpus" provenance tag added to the /admin/pipeline/ list table, positioned between Status and Created, using only pre-existing color tokens.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-07-10T16:30:00Z
- **Completed:** 2026-07-10T21:15:00Z
- **Tasks:** 2 (1 auto + 1 checkpoint:human-verify)
- **Files modified:** 1

## Accomplishments
- Added `sourceLabel(source)` and `sourceTagStyle()` helpers in `app/src/routes/admin/pipeline/+page.svelte`, mirroring the existing `badgeStyle`/`badgeLabel` derived-tag pattern.
- Inserted a new `Source` `<th>`/`<td>` column between Status and Created, rendering a static, non-interactive neutral tag (`#94a3b8` border/text on `#0f1117`) per row.
- Checkpoint verification confirmed the column renders correctly for PDF-ingested jobs and does not regress any other page region (New Run card, mode toggle, "Show incomplete only" toggle, empty states).

## Task Commits

Each task was committed atomically:

1. **Task 1: Add sourceLabel/sourceTagStyle helpers and the new Source column** - `6574e7b4` (feat)
2. **Task 2: Visual verification of the Source column on the Pipeline list** - checkpoint, no code change; approved by user (see Deviations/Issues below)

**Plan metadata:** (this commit) — docs: complete plan

## Files Created/Modified
- `app/src/routes/admin/pipeline/+page.svelte` - Added `sourceLabel()`/`sourceTagStyle()` helpers and the Source `<th>`/`<td>` column (Status | Source | Created | View)

## Decisions Made
- Verification for Task 2 was completed via direct dev-database inspection (querying `admin_jobs`/`arguments` rows) combined with reviewing the rendered PDF-row tags, rather than a live click-through showing both PDF and Corpus tags side by side — because the dev database currently holds zero corpus-imported `AdminJob` rows (see Deviations). The user reviewed this explanation and responded "approved."

## Deviations from Plan

None to the code itself — plan executed exactly as written (helpers, column position, styling, and copy all match the UI-SPEC/plan verbatim, confirmed via `git show --stat 6574e7b4`: 35 insertions, 1 file, no new hex values, no detail-page/filter/bulk change).

### Verification-process note (not a code deviation)

**1. Corpus-imported rows are not visible in the current Pipeline list — expected, not a defect of this plan**
- **Found during:** Task 2 (checkpoint verification)
- **Issue:** The user reported the Source column renders correctly for PDF-ingested jobs, but no corpus-imported jobs appear anywhere in the /admin/pipeline/ list to confirm the "Corpus" tag rendering.
- **Root cause (confirmed via direct dev-DB inspection):** The ~163 corpus-imported arguments currently in the database were imported by Phase 29's `import_convokit.py`, before plan 30-01 (which added the paired `AdminJob` insert for corpus imports) existed. These rows therefore have no `AdminJob` row and remain at `Argument.status = draft` — invisible to the Pipeline list, which is a listing of `AdminJob` rows, not `Argument` rows.
- **This is exactly the D-02 problem plan 30-04 (next, Wave 3) exists to fix** via a wipe-and-rerun of the corpus import now that 30-01/30-02 are in place. It is not a bug introduced by 30-03's Source-column code.
- **Resolution:** No code change required in this plan. Documented here and communicated to the user, who reviewed and responded "approved" to proceed with plan completion. Full visual confirmation of the "Corpus" tag rendering against a real corpus-imported `AdminJob` row is deferred to occur naturally once plan 30-04 re-imports the corpus data.
- **Files modified:** None (investigation only, no code change)
- **Verification:** `sourceLabel('corpus') === 'Corpus'` and `sourceLabel('pdf') === 'PDF'` confirmed by direct code read of the committed helper; PDF-row rendering confirmed visually in the dev environment; Corpus-row rendering will be confirmed once 30-04 repopulates paired AdminJob rows for corpus imports.

---

**Total deviations:** 0 code deviations; 1 verification-process note (expected data-state gap, tracked forward to plan 30-04).
**Impact on plan:** None. The plan's code deliverable is complete and correct as written; the empty-corpus-row observation is a downstream data-migration concern owned entirely by plan 30-04.

## Issues Encountered
- Dev database currently has no corpus-imported `AdminJob` rows to visually confirm the "Corpus" tag against (see Deviations above) — resolved by direct DB inspection plus user approval to proceed, with full confirmation deferred to plan 30-04.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Plan 30-04 (wipe-and-rerun of the corpus import) is unblocked and will populate paired `AdminJob` rows for corpus-imported arguments, at which point the "Corpus" tag rendering can be visually confirmed end-to-end in the Pipeline list.
- No blockers for this plan's own scope.

---
*Phase: 30-corpus-import-resolve-workflow*
*Completed: 2026-07-10*

## Self-Check: PASSED
- FOUND: app/src/routes/admin/pipeline/+page.svelte
- FOUND: commit 6574e7b4
- FOUND: .planning/phases/30-corpus-import-resolve-workflow/30-03-SUMMARY.md
