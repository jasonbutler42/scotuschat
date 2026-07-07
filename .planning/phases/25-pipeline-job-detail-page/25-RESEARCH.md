# Phase 25: Pipeline Job Detail Page - Research

**Researched:** 2026-07-07
**Domain:** SvelteKit admin workflow UI plus FastAPI admin job/resolve services
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Run Status Card States
- **D-01:** Use a hybrid run status card. When action is needed, it behaves like an operator checklist. Once an argument is already created, it becomes a summary/provenance handoff.
- **D-02:** The Not ready state uses strict blockers before Create Argument is available: linked argument exists, metadata has at least docket/question/date, resolve rows are dispositioned, and no failed/current running step is blocking creation.
- **D-03:** The Ready state primary CTA is `Create Argument`. It keeps the existing product language and transitions `argument.status` from `pipeline` to `draft`.
- **D-04:** The Already created state shows only that the argument was created plus a link to `/admin/arguments/[id]`. Do not include rerun in this state.

#### Failed Step Recovery
- **D-05:** A failed run should not offer `Re-run with same source` as the primary failed-card action. If a run failed, identical settings are unlikely to change the outcome.
- **D-06:** Failed cards should show contextual guidance when available, otherwise route the operator back to start a new run from `/admin/pipeline/` after correcting inputs.
- **D-07:** Guidance should be step-specific: Ingest points to PDF/source checks, Parse points to transcript format or LLM failure, and Resolve points to aliases/people data.
- **D-08:** Show human guidance first. Put the raw technical error in an expandable/details block.
- **D-09:** Keep Danger Zone unchanged for failed jobs. It remains the last card and delete-run behavior stays scoped to the admin job row.

#### Resolve Card Interaction Model
- **D-10:** Preserve the current mostly automatic matching flow. The system should prefill parser/system inference and auto-matches where it can, with operator override available.
- **D-11:** Rows that need intervention should guide the operator through side selection before person selection, but the whole resolve workflow should not become manual when the system already knows enough.
- **D-12:** The inline `Create new person` flow should become a mini popover/dialog in Phase 25. It captures name plus Bench/Advocate side only, sets `Person.is_justice` and `ArgumentParticipant.side`, then sends full details to People editor later.
- **D-13:** Do not pull the full Phase 27 create-person editor into this phase.
- **D-14:** Advocate Argument Role and Title are editable before Create Argument, with extracted hints visible. Prefer inline table controls; edit-on-demand is acceptable if the planner finds inline controls too dense.
- **D-15:** Bench participants show tenure-derived role when available. If no matching tenure exists, show `Missing tenure` in the role column plus a link to the person editor. Do not add inline tenure editing here.
- **D-16:** The Missing tenure pattern may generalize to people editing/viewing: surface person-related gaps in context with a direct path to the person editor, instead of ad hoc inline editing everywhere.
- **D-17:** Saving Argument Details, especially argued date, should immediately refresh resolve-card data and update tenure-derived roles without requiring a full page reload.

#### Post-Creation Read-Only Model
- **D-18:** Once an argument has been created, the pipeline job detail page becomes a read-only provenance page. The run exists for historical reasons.
- **D-19:** No resolve or metadata editing remains available on an already-created run page.
- **D-20:** Remove `Re-run with same source` from already-created run pages. New runs start from `/admin/pipeline/`.
- **D-21:** Historical job pages still show full provenance: run status card, source PDF, step cards/results, failed/details if relevant, argument editor link, and Danger Zone.
- **D-22:** Danger Zone remains available after argument creation, but delete still means delete the admin job row only. Argument and pipeline data survive, matching current backend behavior.

### the agent's Discretion
- The planner may decide whether advocate role/title controls are always inline or edit-on-demand, as long as they are editable before Create Argument and extracted hints remain visible.
- Exact copy for step-specific failure guidance is open, but it must be practical and tied to the failed step.
- The visual structure of the create-person popover is open, as long as Phase 25 stays to mini-popover scope and does not become the full person editor.

### Deferred Ideas (OUT OF SCOPE)
- **Bug:** Source PDF reuse should not be blocked across multiple pipeline runs. The system currently prevents using a source PDF for more than one pipeline run, but that should not be a hard requirement.
- Full create-person interface belongs to Phase 27 People Admin, not Phase 25.
</user_constraints>

## Summary

Phase 25 is a targeted restructure of the existing `/admin/pipeline/[job_id]` page, not a new pipeline feature. The current page already has the raw ingredients: Svelte 5 runes, `use:enhance` form actions, live job polling, step status cards, an `ArgumentDetailsCard`, resolve discrepancy state, approve/rerun/delete actions, and API endpoints for job detail, PDF, resolve, participants, approve, rerun, inline person creation, and delete. The plan should move actions into the cards required by the UI spec and add narrowly scoped data support for readiness blockers, richer resolve rows, mini create-person side/is_justice, and read-only provenance. [VERIFIED: codebase]

The highest-risk work is the resolve card. The existing discrepancy response is JSONB-backed and candidate-centric, while Phase 25 needs row-level side, title, tenure-derived bench role, missing-tenure status, action state, and read-only behavior after creation. Do not try to infer all of this in the browser from partial data. Add explicit backend/service/schema fields and let Svelte render the returned shape. [VERIFIED: codebase]

**Primary recommendation:** Split the phase into backend shape support first, then componentized UI cards, then action relocation/read-only gating, then focused tests; keep `ArgumentDetailsCard`, `DocketPillInput`, and Danger Zone behavior unchanged. [VERIFIED: codebase]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| Readiness blockers for Create Argument | API / Backend | Frontend Server | Backend owns job, argument, participant, and step facts; SvelteKit load should pass the computed state to the client. [VERIFIED: codebase] |
| Run status card rendering | Browser / Client | Frontend Server | Svelte renders the card from loaded job/argument data and submits existing actions through form actions. [VERIFIED: codebase] |
| Failed-step guidance | Browser / Client | API / Backend | UI copy is presentation logic, but failed step and raw error come from `AdminJob.current_step` and `error_message`. [VERIFIED: codebase] |
| Resolve row data | API / Backend | Browser / Client | Person, participant, title, side, and tenure lookup require database joins; the browser should not derive tenure coverage from incomplete data. [VERIFIED: codebase] |
| Mini create-person side/is_justice | API / Backend | Browser / Client | The backend must persist `Person.is_justice` and participant side under job/argument guards; the UI collects only name and side. [VERIFIED: codebase] |
| Read-only provenance after creation | Browser / Client | API / Backend | Backend already blocks double-approve; UI must hide/edit-disable metadata, resolve, and rerun controls based on argument status. [VERIFIED: codebase] |
| Delete run Danger Zone | API / Backend | Browser / Client | Existing delete endpoint intentionally removes only `admin_jobs`; UI must leave this final card unchanged. [VERIFIED: codebase] |

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PJOB-01 | Pipeline Run status card: status badge + source file linked to PDF replaces preview card | Use `AdminJobResponse.status`, `current_step`, `original_filename`, `pdf_url`/`/jobs/{id}/pdf`, and loaded argument status. [VERIFIED: codebase] |
| PJOB-02 | Run status card states: Not ready / Ready / Already created | Add server-side readiness derivation in `+page.server.ts` or FastAPI response; Ready depends on metadata, resolve rows, and non-running/non-failed job state. [VERIFIED: codebase] |
| PJOB-08 | Failed step card shows error plus contextual actions inside card | Move current failed panel into the failed step card; use UI-SPEC guidance copy and raw error disclosure. [VERIFIED: codebase] |
| PJOB-14 | Resolve card editable in Not ready/Ready, read-only in Already created | Gate controls by `argument.status === 'pipeline'`; render read-only row cells otherwise. [VERIFIED: codebase] |
| PJOB-15 | Resolve card columns locked | Replace current table with Raw label, Resolved as, Bench/Advocate, Argument Role, Title, Action. [VERIFIED: codebase] |
| PJOB-16 | Bench role tenure lookup or Missing tenure | Add backend join against `court_tenures` using `Argument.argued_date`; expose derived role/missing-tenure state. [VERIFIED: codebase] |
| PJOB-17 | Saving Argument Details recalculates bench roles | After `saveJobMetadata`, call `update({ reset: false })` plus `invalidateAll()` or equivalent parent refresh so changed argued date updates loaded resolve data. [VERIFIED: codebase] |
| PJOB-18 | Side selection before person selection | Update row state and controls to capture Bench/Advocate first for unresolved rows, without breaking auto-matched rows. [VERIFIED: codebase] |
| PJOB-19 | Mini create-person Name + side sets `is_justice` and participant side | Extend `PersonCreate` and `create_person_for_job`; update the specific participant side/person in the same guarded flow or immediately after creation. [VERIFIED: codebase] |
| PJOB-20 | Create Argument lives in run status card | Move the existing `approve` form into the Ready state of `RunStatusCard`. [VERIFIED: codebase] |
| PJOB-21 | Continue Resolve lives at bottom of resolve card | Move existing `resolve` form into `ResolveCard` footer when all rows are dispositioned. [VERIFIED: codebase] |
| PJOB-22 | Re-run lives inside failed step card per older wording | Phase 25 context/UI-SPEC supersede this: do not make same-source rerun the primary failed-state recovery action; guide to corrected new run and remove already-created rerun. [VERIFIED: 25-UI-SPEC.md] |
| PJOB-23 | Danger Zone delete run unchanged | Keep the existing final card and existing `delete` action semantics. [VERIFIED: codebase] |
</phase_requirements>

## Project Constraints (from AGENTS.md)

No `AGENTS.md` exists at the project root, and no project skill directory was present under `.codex/skills` or `.agents/skills`. [VERIFIED: filesystem]

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Svelte | `^5.30.0` | Page and component rendering using runes | Existing admin pages and components already use `$props`, `$state`, `$derived`, and `$effect`; preserve this. [VERIFIED: app/package.json, codebase] |
| SvelteKit | `^2.21.0` | Server load functions, form actions, routing | Existing `+page.server.ts` loads job/people/participants/argument data and owns form actions. [VERIFIED: app/package.json, codebase] |
| FastAPI + Pydantic v2 | Existing backend stack | Admin JSON/form endpoints and response schemas | Current admin routes use typed Pydantic request/response models and service functions. [VERIFIED: api/routers/admin.py, api/schemas/admin_jobs.py] |
| SQLAlchemy async ORM | Existing backend stack | Database joins and guarded updates | Services use `AsyncSession`, `select`, `update`, `delete`, and `synchronize_session=False` guards. [VERIFIED: api/services/admin_jobs.py, api/services/admin_people.py] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| bits-ui | `^2.18.1` | Accessible popover/dialog primitives | Use only if native HTML/Svelte is not enough for the create-person popover/dialog. [VERIFIED: app/package.json, 25-UI-SPEC.md] |
| pytest | Existing Python test runner | Backend/service/schema tests | Existing test infrastructure covers admin jobs, people, arguments, parser, and models. [VERIFIED: pytest.ini, tests] |
| svelte-check | `^4.2.0` | Svelte/TypeScript validation | Run from `app` after page/component edits. [VERIFIED: app/package.json] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Backend-derived resolve row shape | Browser-only derivation from `data.participants`, `data.people`, and `liveJob.discrepancies` | Browser-only logic cannot reliably compute tenure coverage or persist side/title changes; backend shape is safer. [VERIFIED: codebase] |
| Existing page monolith only | Extract `RunStatusCard`, `ResolveCard`, `FailedStepGuidance`, `CreatePersonPopover` | Extraction reduces risk on a 1,400+ line page and matches UI-SPEC recommended decomposition. [VERIFIED: codebase, 25-UI-SPEC.md] |
| New component/icon package | Install a UI/icon dependency | UI-SPEC explicitly forbids new icon package/registry blocks; `bits-ui` already exists if needed. [VERIFIED: 25-UI-SPEC.md] |

**Installation:** No external package installation is recommended for Phase 25. [VERIFIED: app/package.json, 25-UI-SPEC.md]

## Package Legitimacy Audit

No new external packages should be installed in this phase. Existing dependencies (`svelte`, `@sveltejs/kit`, `bits-ui`) are already present in `app/package.json`; planner should not add registry blocks, icon libraries, or visual component packages. [VERIFIED: app/package.json, 25-UI-SPEC.md]

## Architecture Patterns

### System Architecture Diagram

```text
Operator opens /admin/pipeline/[job_id]
  -> SvelteKit load fetches FastAPI job, people, participants, argument
  -> FastAPI services derive job status, parse stats, participant/resolve facts
  -> Page renders sibling cards:
       Run status -> Argument Details -> Step cards -> Resolve -> Provenance -> Danger Zone
  -> Operator saves metadata / resolves speakers / creates person / creates argument
  -> SvelteKit form action calls FastAPI endpoint with X-Admin-Token
  -> FastAPI validates job + argument ownership, mutates DB, returns typed response
  -> SvelteKit update/invalidate refreshes loaded data and live resolve status
```

### Recommended Project Structure

```text
app/src/routes/admin/pipeline/[job_id]/
  +page.server.ts        # load/action orchestration only
  +page.svelte           # page composition and shared state
app/src/lib/components/
  ArgumentDetailsCard.svelte     # preserve existing behavior
  DocketPillInput.svelte         # preserve existing behavior
  RunStatusCard.svelte           # recommended new workflow card
  ResolveCard.svelte             # recommended new resolve table/card
  FailedStepGuidance.svelte      # optional small guidance unit
  CreatePersonPopover.svelte     # optional focused mini-flow
api/schemas/
  admin_jobs.py          # enrich response/request schemas for resolve/create-person
  admin_people.py        # enrich ParticipantItem or add phase-specific row schema
api/services/
  admin_jobs.py          # readiness, resolve job mutation, mini create-person support
  admin_people.py        # participant/tenure lookup support
```

### Pattern 1: SvelteKit Form Actions Remain the Mutation Boundary

**What:** Keep browser submissions as `<form method="POST" use:enhance>` actions handled by `+page.server.ts`, which then calls FastAPI with `X-Admin-Token`. [VERIFIED: codebase]

**When to use:** `saveJobMetadata`, `resolve`, `approve`, `addPerson`, and `delete` should remain form actions rather than direct browser-to-FastAPI calls. [VERIFIED: codebase]

**Example:**
```typescript
use:enhance={() => {
  submitting = true;
  return async ({ result, update }) => {
    submitting = false;
    await update({ reset: false });
  };
}}
```

### Pattern 2: Backend-Derived Readiness and Resolve Rows

**What:** Add a typed data shape for run status blockers and resolve rows instead of spreading condition logic across the Svelte page. [VERIFIED: codebase]

**When to use:** Create Argument readiness, read-only status, bench tenure role, missing-tenure warning, row side/title/action state. [VERIFIED: codebase]

**Recommended shape:**
```typescript
type RunReadiness = {
  state: 'not_ready' | 'ready' | 'already_created';
  blockers: string[];
  canCreateArgument: boolean;
  argumentEditHref?: string;
};

type ResolveRow = {
  raw_speaker_label: string;
  person_id: number | null;
  person_name: string | null;
  photo_url?: string | null;
  side: 'BENCH' | 'PETITIONER' | 'RESPONDENT' | 'AMICUS' | 'ADVOCATE' | 'UNKNOWN';
  argument_role: string | null;
  title: string | null;
  title_hint: string | null;
  bench_role: string | null;
  missing_tenure: boolean;
  editable: boolean;
};
```

### Pattern 3: Read-Only Provenance Is a Page Mode

**What:** Compute a single `alreadyCreated`/`readonly` page mode from `argument.status !== 'pipeline'`, then pass it down to cards. [VERIFIED: codebase]

**When to use:** `ArgumentDetailsCard` already accepts `readonly`; the resolve card should follow the same mode. Hide rerun and mutation controls when this mode is true. [VERIFIED: app/src/lib/components/ArgumentDetailsCard.svelte]

### Pattern 4: Preserve Polling but Refresh Full Load on Terminal or Metadata Save

**What:** Existing polling updates `liveJob` every second and calls `invalidateAll()` when a terminal status is reached. Metadata save needs the same full-load refresh path because bench tenure role depends on `Argument.argued_date`, not just job status. [VERIFIED: codebase]

**When to use:** On successful `saveJobMetadata`, call `update({ reset: false })` and trigger parent refresh/invalidation so resolve row tenure data re-renders immediately. [VERIFIED: codebase]

### Anti-Patterns to Avoid

- **Do not redesign `ArgumentDetailsCard` or `DocketPillInput`:** They already implement the Phase 23/24 contracts; only pass `readonly` or refresh integration as needed. [VERIFIED: codebase]
- **Do not leave page-level floating actions:** `Create Argument`, `Continue Resolve`, and failed recovery must live inside the relevant cards. [VERIFIED: 25-UI-SPEC.md]
- **Do not keep already-created rerun:** Context and UI-SPEC supersede older PJOB-22 language; remove same-source rerun from historical pages. [VERIFIED: 25-UI-SPEC.md]
- **Do not derive tenure role in Svelte:** Tenure lookup needs DB date-window logic against `court_tenures`. [VERIFIED: api/models/models.py]
- **Do not make mini create-person a full editor:** Name plus Bench/Advocate side only; Phase 27 owns full person creation/editing. [VERIFIED: 25-CONTEXT.md]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Dialog/popover focus management | Custom global keyboard/focus trap if it grows complex | Existing `bits-ui` dependency or native dialog semantics | UI-SPEC allows bits-ui if needed and accessibility requires focus trapping/return. [VERIFIED: app/package.json, 25-UI-SPEC.md] |
| DB tenure lookup in browser | Client-side date math from partial arrays | SQLAlchemy service query against `CourtTenure` and `Argument.argued_date` | Backend has full data and already implements tenure-gap query patterns. [VERIFIED: api/services/admin_people.py] |
| API authorization bypass | Browser calls FastAPI admin endpoints directly | Existing SvelteKit server actions with `ADMIN_TOKEN` | Current pattern keeps admin token server-side. [VERIFIED: app/src/routes/admin/pipeline/[job_id]/+page.server.ts] |
| Run delete cascade | Deleting argument/pipeline data from job delete | Existing `delete_job` service | Phase 25 requires Danger Zone unchanged and service deletes only `admin_jobs`. [VERIFIED: api/services/admin_jobs.py] |

**Key insight:** This phase is mostly data-shape and component-boundary work. The planner should avoid broad pipeline changes and isolate database mutations to existing admin service patterns. [VERIFIED: codebase]

## Existing Implementation Findings

### Current UI Surface

- `+page.svelte` is currently a large monolithic page containing job polling, step card helpers, discrepancy row state, resolve forms, approve form, rerun form, failed panel, participant list, and Danger Zone. [VERIFIED: app/src/routes/admin/pipeline/[job_id]/+page.svelte]
- `ArgumentDetailsCard` is already rendered when `data.argument != null`, owns its form, uses `DocketPillInput`, accepts `readonly`, and hides its save button in readonly mode. [VERIFIED: app/src/lib/components/ArgumentDetailsCard.svelte]
- `Continue Resolve` currently sits below the step cards as a page-level form, and `Create Argument` currently sits as a page-level approve form. Both need relocation. [VERIFIED: app/src/routes/admin/pipeline/[job_id]/+page.svelte]
- A post-approval `Re-run with same source` control exists today and must be removed from already-created pages. [VERIFIED: app/src/routes/admin/pipeline/[job_id]/+page.svelte]
- Failed state currently renders as a separate bottom panel with technical error and `Start a new run`; it needs to move into/adjacent to the failed step card with human guidance first and raw error in details. [VERIFIED: app/src/routes/admin/pipeline/[job_id]/+page.svelte, 25-UI-SPEC.md]
- Danger Zone is already the final card and uses a two-step confirm around the `delete` action; keep it unchanged and last. [VERIFIED: app/src/routes/admin/pipeline/[job_id]/+page.svelte]

### Current Load/Action Surface

- `+page.server.ts` loads `job`, broad `people`, `participants`, `argument`, `savedValues`, and `hints`; it degrades gracefully on non-critical people/participant/argument failures. [VERIFIED: app/src/routes/admin/pipeline/[job_id]/+page.server.ts]
- Actions already exist for `resolve`, `approve`, `rerun`, `addPerson`, `delete`, and `saveJobMetadata`. Phase 25 should keep the action pattern but change UI placement and extend payloads where needed. [VERIFIED: app/src/routes/admin/pipeline/[job_id]/+page.server.ts]
- `saveJobMetadata` derives `argument_id` from the job server-side, reads `docket[]`, and PATCHes `/api/admin/arguments/{id}/metadata`; it currently returns `{ saved: true }` but does not explicitly refresh resolve rows after metadata changes. [VERIFIED: app/src/routes/admin/pipeline/[job_id]/+page.server.ts]

### Current Backend Surface

- `AdminJobResponse` exposes status, current step, argument id, PDF/source fields, `source_dockets`, parse stats, raw discrepancies JSON, and error message. It does not expose run readiness or typed resolve rows. [VERIFIED: api/schemas/admin_jobs.py]
- `get_job` attaches parse stats and reads cover metadata/question number, but does not compute readiness blockers or tenure-derived resolve roles. [VERIFIED: api/services/admin_jobs.py]
- `list_participants_for_job` returns only resolved participants and only participant id, person id, full name, role name, and side. It omits title, photo, raw label, utterance count, and tenure status. [VERIFIED: api/services/admin_people.py]
- `PersonCreate` currently accepts `full_name`, optional `role_id`, and optional `role_name`; it does not accept side or `is_justice`. [VERIFIED: api/schemas/admin_jobs.py]
- `create_person_for_job` currently creates a `Person` and optional role only when the job is paused; it does not set `is_justice` or attach the new person to a specific participant row. [VERIFIED: api/services/admin_jobs.py]
- Participant side update endpoint exists but explicitly rejects `BENCH`, because it was built for advocate side updates. Phase 25 needs a separate guarded path or an extension for resolve-specific bench/advocate assignment. [VERIFIED: api/routers/admin.py, api/services/admin_arguments.py]
- `ArgumentParticipant.title` exists from Phase 22, so advocate title editing does not need a migration. [VERIFIED: api/models/models.py]

## Recommended Plan Boundaries

1. **Backend data shapes first:** Add typed readiness and resolve-row support in API/service/schema tests before UI refactor. Include title, side, missing tenure, tenure role, and readonly flags. [VERIFIED: codebase]
2. **Server load/action integration second:** Update `+page.server.ts` to load the new shape and to refresh after metadata save; extend `addPerson` payload only after backend supports side/is_justice. [VERIFIED: codebase]
3. **UI card extraction third:** Add `RunStatusCard`, `ResolveCard`, and optional `FailedStepGuidance`/`CreatePersonPopover`, preserving Svelte 5 runes, inline dark CSS, and `use:enhance`. [VERIFIED: codebase]
4. **Action relocation fourth:** Move `approve` into Run Status Ready state, `resolve` into Resolve footer, and failed guidance into the failed step card. Remove already-created rerun. [VERIFIED: 25-UI-SPEC.md]
5. **Read-only/provenance hardening last:** Ensure already-created pages hide metadata/resolve/rerun controls but keep source PDF, status, step cards, participant/provenance data, argument editor link, and final Danger Zone. [VERIFIED: 25-CONTEXT.md]

## Likely Wave Ordering

| Wave | Scope | Rationale |
|------|-------|-----------|
| Wave 1 | Backend schemas/services/tests for readiness, resolve rows, tenure lookup, mini create-person payload | UI depends on stable data; this is the riskiest contract work. [VERIFIED: codebase] |
| Wave 2 | `+page.server.ts` load/action wiring and metadata-save refresh behavior | Bridges backend shape to components and closes PJOB-17. [VERIFIED: codebase] |
| Wave 3 | Component extraction: RunStatusCard, ResolveCard, FailedStepGuidance, optional CreatePersonPopover | Reduces monolith risk and aligns with UI-SPEC. [VERIFIED: 25-UI-SPEC.md] |
| Wave 4 | Page composition, action relocation, failed/read-only/Danger Zone verification | Keeps final visual/state behavior focused after contracts are stable. [VERIFIED: codebase] |

If `workflow.use_worktrees=false` remains active from prior GSD context, wave-grouped work may still execute sequentially in the main tree. [VERIFIED: memory]

## Common Pitfalls

| Pitfall | Why It Matters | Guard |
|---------|----------------|-------|
| Treating PJOB-22 as same-source rerun requirement | Context/UI-SPEC intentionally supersede this older wording | Failed card should guide corrected new run; already-created rerun is removed. [VERIFIED: 25-UI-SPEC.md] |
| Creating readiness blockers only in Svelte | Browser can miss backend truth about failed/running steps, argument status, or participant state | Derive blockers from loaded backend facts and test service helpers. [VERIFIED: codebase] |
| Losing docket pill state on save | `DocketPillInput` relies on hidden inputs and key/reseed behavior | Preserve `ArgumentDetailsCard` behavior and use `update({ reset: false })`. [VERIFIED: app/src/lib/components/ArgumentDetailsCard.svelte] |
| Updating participant side/title without ownership guard | Cross-argument mutation would be an IDOR risk | Follow existing participant endpoint pattern: participant must belong to argument/job. [VERIFIED: api/routers/admin.py] |
| Setting BENCH through the old advocate-side endpoint | Existing endpoint rejects BENCH by design | Add a resolve-specific endpoint/action path or service function for side + person assignment. [VERIFIED: api/services/admin_arguments.py] |
| Forgetting title persistence | `ArgumentParticipant.title` exists but no current update endpoint covers it | Add explicit allow-listed title update for resolve rows. [VERIFIED: api/models/models.py] |
| Full page reload after metadata save | UX requires immediate bench-role recalculation without manual reload | Use existing invalidate/update pattern after successful save. [VERIFIED: codebase] |
| Moving or changing Danger Zone | UI-SPEC and context require unchanged final card | Leave existing delete action and card placement intact. [VERIFIED: 25-UI-SPEC.md] |

## Code Examples

### Readiness Blocker Function

```typescript
const blockers = [
  !job.argument_id && 'No linked argument yet',
  !savedValues.dockets.length && 'Add at least one docket',
  !savedValues.question_number && 'Add a question number',
  !savedValues.argued_date && 'Add an argued date',
  !resolveRows.every((r) => r.person_id && r.side) && 'Finish resolving speakers',
  liveJob.status === 'failed' && 'Resolve the failed pipeline step',
  liveJob.status === 'running' && 'Wait for the current step to finish',
].filter(Boolean);
```

Use this as a shape example only; the final implementation should prefer a typed helper and avoid duplicating blocker logic across components. [VERIFIED: codebase]

### Tenure Lookup Predicate

```python
covering_tenure = exists(
    select(CourtTenure.id).where(
        and_(
            CourtTenure.person_id == ArgumentParticipant.person_id,
            CourtTenure.start_date <= Argument.argued_date,
            or_(CourtTenure.end_date.is_(None), CourtTenure.end_date >= Argument.argued_date),
        )
    )
)
```

This mirrors the existing tenure-gap service pattern and should be adapted to expose per-row `bench_role` / `missing_tenure`. [VERIFIED: api/services/admin_people.py]

### Mini Create-Person Payload

```json
{
  "raw_speaker_label": "JUSTICE JACKSON",
  "full_name": "Ketanji Brown Jackson",
  "side": "BENCH"
}
```

Backend should convert `side === "BENCH"` to `Person.is_justice = true` and `ArgumentParticipant.side = BENCH`; advocate sides should keep `is_justice = false` and use the selected non-bench side. [VERIFIED: 25-UI-SPEC.md]

## Environment Availability

This phase is code/config-only and depends on the existing repo runtimes rather than new external services. [VERIFIED: codebase]

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Node/npm | SvelteKit checks/build | Not probed in this bounded research run | See `app/package.json` | Planner can use existing project commands. |
| Python/pytest | Backend tests | Not probed in this bounded research run | See `pytest.ini` | Existing test files include import-only tests that run without DB. |
| Database | DB-backed tests/manual UAT | Environment-dependent | `DATABASE_URL` controls skips | Structural/schema tests remain useful without DB. [VERIFIED: tests] |

**Missing dependencies with no fallback:** None identified for planning. [VERIFIED: codebase]

**Missing dependencies with fallback:** DB-backed tests are skipped when `DATABASE_URL` is not configured; use structural tests plus targeted service tests where DB is available. [VERIFIED: tests]

## Validation Architecture

`workflow.nyquist_validation` is explicitly `false` in `.planning/config.json`, so the required GSD Validation Architecture section is skipped. [VERIFIED: .planning/config.json]

Recommended verification despite Nyquist being disabled:

| Area | Command / Check | Notes |
|------|-----------------|-------|
| Svelte typecheck | `cd app; npm run check` | Validates Svelte 5 runes and component props. [VERIFIED: app/package.json] |
| Backend targeted tests | `.\\.venv\\Scripts\\python.exe -m pytest api/tests/test_admin_jobs_stats.py api/tests/test_admin_people_schemas_service.py api/tests/test_admin_jobs_service.py -q` | Extend these or add adjacent tests for new schemas/service helpers. [VERIFIED: pytest.ini] |
| Full backend suite | `.\\.venv\\Scripts\\python.exe -m pytest` | Configured in `.planning/config.json`; may skip DB tests without `DATABASE_URL`. [VERIFIED: .planning/config.json, pytest.ini] |
| Manual UI smoke | Open `/admin/pipeline/[id]` for not-ready, paused, failed, and already-created runs | Required because no frontend e2e suite was found in bounded inputs. [VERIFIED: codebase] |

## Security Domain

`security_enforcement` is absent from `.planning/config.json`, so treat security review as enabled. [VERIFIED: .planning/config.json]

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | yes | Keep FastAPI admin endpoints behind `X-Admin-Token` and SvelteKit server actions; do not expose `ADMIN_TOKEN` to the browser. [VERIFIED: codebase] |
| V3 Session Management | indirect | Preserve existing admin auth/session boundary; no new session feature in scope. [VERIFIED: codebase] |
| V4 Access Control | yes | Derive `argument_id` from `job_id`; participant updates must prove participant belongs to the job's argument. [VERIFIED: codebase] |
| V5 Input Validation | yes | Use Pydantic request models and enum fields for side/status/title payloads; reject malformed IDs/sides. [VERIFIED: codebase] |
| V6 Cryptography | no | No crypto changes in this phase. [VERIFIED: codebase] |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| IDOR on participant/person updates | Elevation of privilege | Resolve-specific mutation must load job -> argument -> participant and update only rows under that argument. [VERIFIED: api/routers/admin.py] |
| Mass assignment on person/participant fields | Tampering | Add explicit Pydantic allow-lists; do not accept arbitrary `Person` or `ArgumentParticipant` fields. [VERIFIED: api/schemas/admin_people.py, api/schemas/admin_arguments.py] |
| Admin token exposure | Information disclosure | Keep all FastAPI admin calls in `+page.server.ts` actions/load. [VERIFIED: app/src/routes/admin/pipeline/[job_id]/+page.server.ts] |
| Raw error display overflow/injection-like UX | Information disclosure / UX denial | Put raw errors in expandable technical details with `white-space: pre-wrap` and `word-break: break-word`; show human guidance first. [VERIFIED: 25-UI-SPEC.md] |

## Open Questions (RESOLVED)

1. **Should resolve row mutations be one endpoint or several?**
   - What we know: Existing endpoints cover resolve submit, inline person create, and advocate side patch; none covers title + BENCH side + person assignment in one typed row update. [VERIFIED: codebase]
   - What's unclear: Whether planner prefers a new job-scoped resolve-row endpoint or extending existing endpoints with stricter guards.
   - Recommendation: Add a job-scoped service/API path for resolve row edits to keep IDOR guards simple and avoid overloading the argument edit participant endpoint.
   - RESOLVED: A single new job-scoped resolve-row mutation is added in Plan 25-01 Task 3 (`update_resolve_row_for_job` service + endpoint on `api/routers/admin.py`, `ResolveRowUpdate` schema in `api/schemas/admin_jobs.py`). It accepts `participant_id`, `side` (BENCH allowed), and optional `title`; derives argument ownership from `job_id`; and does NOT reuse `admin_arguments.update_participant_side` (which rejects BENCH by design). Wired via `saveResolveRow` action in Plan 25-03 and the ResolveCard row controls in Plan 25-04.

2. **How should title edits be submitted?**
   - What we know: `ArgumentParticipant.title` exists and title hints are required for advocate rows. [VERIFIED: api/models/models.py, 25-UI-SPEC.md]
   - What's unclear: Whether title saves should be per-row inline or batched with Continue Resolve.
   - Recommendation: Prefer batched resolve form payload if inline controls are always visible; use per-row save only if edit-on-demand is selected.
   - RESOLVED: Title edits are submitted per-row through the same `saveResolveRow` action/endpoint as side edits (Plan 25-01 Task 3 / 25-03 / 25-04), using inline advocate Title controls per D-14. Bench rows carry `title = null` (enforced both in the read shape in Plan 25-02 and in the write path in Plan 25-01) and their Title cell is hidden in the ResolveCard.

3. **What exact row shape should replace `discrepancies`?**
   - What we know: Current `discrepancies` is a loose JSON list; TypeScript defines a local `Discrepancy` interface. [VERIFIED: app/src/routes/admin/pipeline/[job_id]/+page.svelte, api/schemas/admin_jobs.py]
   - What's unclear: Whether to keep backward-compatible `discrepancies` and add `resolve_rows`, or replace the frontend consumption only.
   - Recommendation: Add `resolve_rows` while leaving `discrepancies` for compatibility during the phase.
   - RESOLVED: Add the typed `ResolveRow` shape / `list_resolve_rows_for_job` in Plan 25-02 and consume it in the ResolveCard, while leaving the legacy `discrepancies` JSON on `AdminJobResponse` intact for backward compatibility during the phase (Plan 25-03 keeps existing consumers until the page composition plan removes them).

## State of the Art

| Old Approach | Current Phase 25 Approach | Impact |
|--------------|---------------------------|--------|
| Page-level `Create Argument` button | CTA inside Run status Ready card | Operator sees creation only when blockers are clear. [VERIFIED: 25-UI-SPEC.md] |
| Page-level `Continue Resolve` button | Resolve card footer action | Resolve workflow stays self-contained. [VERIFIED: 25-UI-SPEC.md] |
| Already-created rerun button | Read-only provenance plus argument editor link | Prevents same-source rerun from historical pages. [VERIFIED: 25-CONTEXT.md] |
| Raw failed panel | Failed step guidance inside failed card | Human guidance first, raw technical details second. [VERIFIED: 25-UI-SPEC.md] |
| Resolve table with confirm/check style | Locked columns with side, role, title, action | Matches v1.5 operator workflow requirements. [VERIFIED: REQUIREMENTS.md] |

**Deprecated/outdated:**
- Same-source rerun as failed recovery primary action is outdated for Phase 25; UI-SPEC explicitly supersedes older PJOB-22 wording. [VERIFIED: 25-UI-SPEC.md]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Node/npm and Python runtimes are available in the execution environment. | Environment Availability | Planner may need to add setup or run-command fallback. |

## Sources

### Primary (HIGH confidence)
- `.planning/ROADMAP.md` - Phase 25 goal, requirements, success criteria, and PJOB-22 tension. [VERIFIED: file read]
- `.planning/REQUIREMENTS.md` - PJOB-01, PJOB-02, PJOB-08, PJOB-14 through PJOB-23. [VERIFIED: file read]
- `.planning/config.json` - Nyquist disabled and test command. [VERIFIED: file read]
- `.planning/phases/25-pipeline-job-detail-page/25-CONTEXT.md` - locked decisions and scope. [VERIFIED: file read]
- `.planning/phases/25-pipeline-job-detail-page/25-UI-SPEC.md` - approved visual/interaction contract and rerun supersession. [VERIFIED: file read]
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` - existing UI/action placement and Svelte 5 patterns. [VERIFIED: file read]
- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` - existing load/action bridge. [VERIFIED: file read]
- `app/src/lib/components/ArgumentDetailsCard.svelte` and `DocketPillInput.svelte` - preserved shared component behavior. [VERIFIED: file read]
- `api/routers/admin.py`, `api/services/admin_jobs.py`, `api/schemas/admin_jobs.py`, `api/services/admin_people.py`, `api/schemas/admin_people.py`, `api/models/models.py` - backend contracts and gaps. [VERIFIED: file read]

### Secondary (MEDIUM confidence)
- Prior Phase 24 memory summary - generic-agent workaround context and reminder that wave grouping may still execute sequentially when worktrees are disabled. [VERIFIED: memory]

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - verified from `app/package.json` and current code.
- Architecture: HIGH - based on direct source reads across SvelteKit and FastAPI seams.
- Pitfalls: HIGH - based on existing code, approved UI spec, and phase context.
- Environment availability: MEDIUM - commands were not probed; project files and tests were inspected.

**Research date:** 2026-07-07
**Valid until:** 2026-08-06 for this codebase snapshot; refresh if Phase 25 planning is delayed past adjacent Phase 26/27 changes.
