# Phase 21: Admin UI Surface - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-01
**Phase:** 21-Admin UI Surface
**Areas discussed:** Delete confirmation flow, Delete button placement, Pipeline run delete cascade, NAV-02 scope

---

## Delete Confirmation Flow

| Option | Description | Selected |
|--------|-------------|----------|
| Inline two-step reveal | First click shows "Confirm delete" + "Cancel"; second click submits. $state-driven, no navigation. | ✓ |
| Dedicated confirmation page | Navigate to /admin/arguments/[id]/delete with a warning card. | |
| Browser confirm() dialog | One-liner JS, can't be styled. | |

**User's choice:** Inline two-step reveal

---

| Option | Description | Selected |
|--------|-------------|----------|
| Block if status = 'published' | Block deletion if published_at IS NOT NULL. | ✓ |
| Block if any utterances exist | Block even for draft arguments with partial parse data. | |
| Never block | Hard delete always allowed. | |

**User's choice:** Block if status = 'published'

---

| Option | Description | Selected |
|--------|-------------|----------|
| Argument delete independent of job state | Only argument.status matters; no check against admin_job. | ✓ |
| Block if a job is still running | Guard: can't delete while admin_job.status = RUNNING. | |
| You decide | Claude picks. | |

**User's choice:** Argument delete is independent of job state

---

## Delete Button Placement

| Option | Description | Selected |
|--------|-------------|----------|
| Argument edit page only (/admin/arguments/[id]) | Consistent with people editor; keeps list page uncluttered. | ✓ |
| Argument list page per-row | Per-row delete; faster but complicates list page state. | |
| Both list and edit page | More surface area for this phase. | |

**User's choice:** Argument edit page only

---

| Option | Description | Selected |
|--------|-------------|----------|
| Job detail page only (/admin/pipeline/[job_id]) | Operator opens job to delete; consistent with argument pattern. | ✓ |
| Pipeline list page per-row | Fast access but complicates per-row state. | |
| Both list and detail page | More surface area. | |

**User's choice:** Job detail page only

---

## Pipeline Run Delete Cascade

| Option | Description | Selected |
|--------|-------------|----------|
| Just the admin_job row | Delete only the job record; pipeline_runs, utterances, and argument are unaffected. | ✓ |
| admin_job + pipeline_runs + utterances | Full cleanup; argument survives but is emptied. | |

**User's choice:** Just the admin_job row

**Notes:** User clarified an important architectural mental model: pipeline runs exist solely to produce an argument. Once the argument is created, it is the permanent record. Pipeline runs are disposable scaffolding with only a historical reference to the argument they created. Deleting a pipeline run must never affect the argument. Saved to memory (project_pipeline_run_mental_model.md). The inverse path (delete bad utterances too) goes through ADMIN-01 (delete argument).

---

## NAV-02 Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Active link highlighting only | Current section link gets accent color; background stays as-is. | |
| Background color alignment + active link | Align admin to public background + active highlights. | |
| Something else | User described a specific layout change. | ✓ |

**User's choice:** Two-row nav structure — public TopNav on Row 1, new AdminSubNav strip on Row 2.

**Notes:** User wants the public TopNav (Cases + Admin link) to always be visible when in the admin area, so the operator can navigate back to the public case list without logging out. A new `AdminSubNav` component renders immediately below with: Pipeline Runner, Arguments, People Editor, Logout (right-aligned). AdminSubNav background: #1e293b (existing admin color) for visual separation from public TopNav (#0f1117). `TopNav.svelte` is not modified; admin layout switches from `<TopNav variant="admin" />` to `<TopNav variant="public" /><AdminSubNav />`.

---

## Claude's Discretion

- None — all decisions made by user.

## Deferred Ideas

None — discussion stayed within phase scope.
