# Phase 25: Pipeline Job Detail Page - Context

**Gathered:** 2026-07-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Restructure `/admin/pipeline/[id]` around the operator's run lifecycle. This phase delivers:

1. A primary run status card with source PDF access, readiness blockers, Create Argument CTA, and already-created handoff state
2. Failed-step recovery inside the failed card with step-specific guidance and raw error details
3. A redesigned resolve card with automatic matching preserved, editable role/title rows, mini create-person popover, tenure warnings, and immediate role recalculation after metadata saves
4. Removal of standalone page-level action buttons: Create Argument and Continue Resolve live in their cards; rerun is removed from already-created historical run pages
5. Existing Danger Zone behavior retained as the last card

This phase does not redesign `ArgumentDetailsCard` / `DocketPillInput` and does not build the full Phase 27 person creation/editor workflow.

</domain>

<decisions>
## Implementation Decisions

### Run Status Card States
- **D-01:** Use a hybrid run status card. When action is needed, it behaves like an operator checklist. Once an argument is already created, it becomes a summary/provenance handoff.
- **D-02:** The Not ready state uses strict blockers before Create Argument is available: linked argument exists, metadata has at least docket/question/date, resolve rows are dispositioned, and no failed/current running step is blocking creation.
- **D-03:** The Ready state primary CTA is `Create Argument`. It keeps the existing product language and transitions `argument.status` from `pipeline` to `draft`.
- **D-04:** The Already created state shows only that the argument was created plus a link to `/admin/arguments/[id]`. Do not include rerun in this state.

### Failed Step Recovery
- **D-05:** A failed run should not offer `Re-run with same source` as the primary failed-card action. If a run failed, identical settings are unlikely to change the outcome.
- **D-06:** Failed cards should show contextual guidance when available, otherwise route the operator back to start a new run from `/admin/pipeline/` after correcting inputs.
- **D-07:** Guidance should be step-specific: Ingest points to PDF/source checks, Parse points to transcript format or LLM failure, and Resolve points to aliases/people data.
- **D-08:** Show human guidance first. Put the raw technical error in an expandable/details block.
- **D-09:** Keep Danger Zone unchanged for failed jobs. It remains the last card and delete-run behavior stays scoped to the admin job row.

### Resolve Card Interaction Model
- **D-10:** Preserve the current mostly automatic matching flow. The system should prefill parser/system inference and auto-matches where it can, with operator override available.
- **D-11:** Rows that need intervention should guide the operator through side selection before person selection, but the whole resolve workflow should not become manual when the system already knows enough.
- **D-12:** The inline `Create new person` flow should become a mini popover/dialog in Phase 25. It captures name plus Bench/Advocate side only, sets `Person.is_justice` and `ArgumentParticipant.side`, then sends full details to People editor later.
- **D-13:** Do not pull the full Phase 27 create-person editor into this phase.
- **D-14:** Advocate Argument Role and Title are editable before Create Argument, with extracted hints visible. Prefer inline table controls; edit-on-demand is acceptable if the planner finds inline controls too dense.
- **D-15:** Bench participants show tenure-derived role when available. If no matching tenure exists, show `Missing tenure` in the role column plus a link to the person editor. Do not add inline tenure editing here.
- **D-16:** The Missing tenure pattern may generalize to people editing/viewing: surface person-related gaps in context with a direct path to the person editor, instead of ad hoc inline editing everywhere.
- **D-17:** Saving Argument Details, especially argued date, should immediately refresh resolve-card data and update tenure-derived roles without requiring a full page reload.

### Post-Creation Read-Only Model
- **D-18:** Once an argument has been created, the pipeline job detail page becomes a read-only provenance page. The run exists for historical reasons.
- **D-19:** No resolve or metadata editing remains available on an already-created run page.
- **D-20:** Remove `Re-run with same source` from already-created run pages. New runs start from `/admin/pipeline/`.
- **D-21:** Historical job pages still show full provenance: run status card, source PDF, step cards/results, failed/details if relevant, argument editor link, and Danger Zone.
- **D-22:** Danger Zone remains available after argument creation, but delete still means delete the admin job row only. Argument and pipeline data survive, matching current backend behavior.

### Agent's Discretion
- The planner may decide whether advocate role/title controls are always inline or edit-on-demand, as long as they are editable before Create Argument and extracted hints remain visible.
- Exact copy for step-specific failure guidance is open, but it must be practical and tied to the failed step.
- The visual structure of the create-person popover is open, as long as Phase 25 stays to mini-popover scope and does not become the full person editor.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Scope and Requirements
- `.planning/ROADMAP.md` - Phase 25 goal, success criteria, and phase boundary.
- `.planning/REQUIREMENTS.md` - PJOB-01, PJOB-02, PJOB-08, PJOB-14 through PJOB-23.

### Prior Decisions
- `.planning/phases/23-shared-argument-details-component/23-CONTEXT.md` - Locks `ArgumentDetailsCard`, docket/question/date behavior, extracted hints, and shared component boundaries.
- `.planning/phases/24-pipeline-list-page/24-CONTEXT.md` - Locks `DocketPillInput`, full run-start docket list handling, compound status badge behavior, and rerun docket preservation.
- `.planning/phases/22-schema-foundations/22-CONTEXT.md` - Defines `argument_participants.title`, SideEnum legacy constraints, status log, and court tenure schema changes.

### Existing Pipeline Job Detail UI
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` - Main Phase 25 UI target. Currently contains page-level `Continue Resolve`, `Create Argument`, post-approval rerun, failed panel, step cards, resolve table, participant list, and Danger Zone.
- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` - Load/actions target. Handles job, people, participants, argument, metadata save, resolve, approve, rerun, addPerson, and delete actions.

### Shared Components
- `app/src/lib/components/ArgumentDetailsCard.svelte` - Existing shared metadata card. Preserve behavior and reuse; do not redesign in Phase 25.
- `app/src/lib/components/DocketPillInput.svelte` - Existing docket pill input extracted in Phase 24; preserve behavior.

### Backend/API
- `api/routers/admin.py` - Admin job routes: jobs, job detail polling, PDF route, resolve, people, participants, approve, rerun, delete, metadata endpoints.
- `api/services/admin_jobs.py` - Job CRUD, parse stats, resolve_job, approve_job, rerun_job, create_person_for_job, list_people.
- `api/schemas/admin_jobs.py` - `AdminJobResponse`, `ParseStats`, `ResolveMatch`, `PersonCreate` schemas.
- `api/services/admin_people.py` - Participant/person lookup service patterns for resolve and editor links.
- `api/schemas/admin_people.py` - `ParticipantItem` shape and person list/detail schemas.
- `api/models/models.py` - `AdminJob`, `Argument`, `ArgumentParticipant`, `Person`, `CourtTenure`, `SideEnum`, `ArgumentStatusEnum` models.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ArgumentDetailsCard.svelte` already renders dockets, question number, argued date, and extracted hints. It should continue feeding argued date changes that trigger resolve-card bench role recalculation.
- `DocketPillInput.svelte` already implements hidden `docket[]` serialization and pill UI. No Phase 25 changes expected unless needed for integration.
- Existing step cards in `+page.svelte` already compute step status from `liveJob.status` and `current_step`; reuse this for provenance and failed-step placement.
- Existing `liveJob` polling and `invalidateAll()` terminal refresh pattern can inform immediate resolve-card refresh after metadata save.
- Existing `addPerson` action creates only full_name and role_name. Phase 25 should evolve the UI/API boundary to set side/is_justice for mini popover scope.

### Established Patterns
- Svelte 5 Runes only: `$props`, `$state`, `$derived`, `$effect`; no legacy `export let` or `$:` blocks.
- Admin UI uses inline dark-theme CSS with card backgrounds `#1e293b`, borders `#334155`, primary text `#e2e8f0`, muted text `#94a3b8`.
- SvelteKit form actions plus `use:enhance` are the established save/submit pattern.
- Server load owns data fetching. Components receive data via props.
- Backend mutations go through FastAPI admin endpoints; SvelteKit server actions never trust client-provided argument IDs when they can derive them from job ID.
- `delete_job` intentionally deletes only the `admin_jobs` row and does not delete argument, pipeline runs, utterances, or participants.

### Integration Points
- Top-level run status card should be added near the page header before `ArgumentDetailsCard` / step cards.
- `Continue Resolve` should move into the resolve card footer when all rows are dispositioned.
- `Create Argument` should move into the run status card Ready state.
- Failed state UI should live inside or adjacent to the failed step card, not as a standalone bottom panel.
- Already-created state should render the page as read-only provenance with an argument editor link and no rerun/metadata/resolve editing.
- Resolve data likely needs richer participant rows: raw label, resolved person avatar/name, side, argument role, title, action, tenure-derived bench role/missing-tenure state, extracted title hints.

</code_context>

<specifics>
## Specific Ideas

- Already-created copy should make the historical nature clear: once an argument is created, the run exists only as provenance.
- Failed run guidance should not encourage retrying identical settings. Start a corrected new run instead.
- Create-person mini popover is a Phase 25 bridge pattern: enough to unblock resolve, not enough to replace People Admin.
- For people gaps, prefer contextual warning plus link to person editor. This may apply beyond Resolve to future people viewing/editing screens.
- Extracted hints should appear for advocate title/role editing in the resolve card, similar to Phase 23's extracted hints for Argument Details.

</specifics>

<deferred>
## Deferred Ideas

- **Bug:** Source PDF reuse should not be blocked across multiple pipeline runs. The system currently prevents using a source PDF for more than one pipeline run, but that should not be a hard requirement.
- Full create-person interface belongs to Phase 27 People Admin, not Phase 25.

</deferred>

---

*Phase: 25-Pipeline Job Detail Page*
*Context gathered: 2026-07-07*
