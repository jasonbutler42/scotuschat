# Phase 8: People Editor - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-17
**Phase:** 8-people-editor
**Areas discussed:** Participant review integration, Missing field definition, Tenure editing scope, Role assignment, Argument metadata scope, Edit form layout

---

## Participant Review Integration

| Option | Description | Selected |
|--------|-------------|----------|
| Extend job detail page | Completed /admin/pipeline/[job_id] gains a "Resolved Participants" section with read-only list + link | |
| Dedicated review page | New /admin/pipeline/[job_id]/participants page with inline mini-forms | |
| People directory only | No special pipeline integration; PEOPLE-04 satisfied by the incomplete filter alone | ✓ |

**User's choice:** People directory only

**Follow-up — link to directory:**

| Option | Description | Selected |
|--------|-------------|----------|
| Add a "Review people" link | Completed job page links to /admin/people?incomplete=1 | ✓ |
| No link needed | Operator navigates manually | |

**Follow-up — link scope:**

| Option | Description | Selected |
|--------|-------------|----------|
| All incomplete people | Link goes to /admin/people?incomplete=1 globally | ✓ |
| This argument's participants only | Filter to people resolved in this run | |

**Follow-up — read-only participant list on job page:**

| Option | Description | Selected |
|--------|-------------|----------|
| Show read-only participant list | Name + role list with "Review people →" link below | ✓ |
| No participants on job page | Job page stays focused on pipeline steps only | |

**Notes:** User chose the simplest approach — no dedicated review page. The "Review people →" link closes the loop from the pipeline runner to the people editor without adding a new route.

---

## Missing Field Definition

| Option | Description | Selected |
|--------|-------------|----------|
| role + bio + photo | Incomplete if role_id IS NULL OR bio_text IS NULL OR photo_url IS NULL; tenure excluded | ✓ |
| bio + photo only | Role already assigned at resolve time | |
| Any non-name field | Includes tenure absence as "missing" | |

**Follow-up — filter UX:**

| Option | Description | Selected |
|--------|-------------|----------|
| Toggle switch at top of page | URL becomes /admin/people?incomplete=1; pre-activated on navigation from job page | ✓ |
| Separate tab/view | Two tabs: All / Incomplete | |
| Filter button/link | Simple link that toggles the URL param | |

**Follow-up — missing indicator per row:**

| Option | Description | Selected |
|--------|-------------|----------|
| Colored badge showing which fields are missing | Amber chips per row: "bio", "photo", "role" | ✓ |
| Simple incomplete indicator | Dot or "Incomplete" label only | |
| No per-row indicator | Completeness only visible when editing | |

**Follow-up — directory columns:**

| Option | Description | Selected |
|--------|-------------|----------|
| Name + Role + missing-fields badge + Edit link | Clean, focused | ✓ |
| Name + Role + Bio snippet + Photo indicator + Edit link | More info, noisier | |
| Name only + Edit link | Minimal | |

---

## Tenure Editing Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Edit existing row only, no create | Fields hidden if no tenure exists | |
| Always show tenure fields, create if needed | Fields always visible; create new row on save if populated | ✓ |
| Separate tenure management | "Manage tenures" sub-section linked from edit form | |

**Follow-up — multiple tenures:**

| Option | Description | Selected |
|--------|-------------|----------|
| Most recent tenure only | Show only the most recent court_tenures row | |
| All tenure rows | Show all rows with add/delete per row | ✓ |

**Follow-up — add/delete UX:**

| Option | Description | Selected |
|--------|-------------|----------|
| Add row button + delete per row | Full CRUD for tenure rows, saved with main form | ✓ |
| Add row button, no delete | Can add but not delete | |
| You decide | Claude picks | |

---

## Role Assignment

| Option | Description | Selected |
|--------|-------------|----------|
| Dropdown from existing roles + "Add new role" option | Inline form to create new role; new role immediately selectable | ✓ |
| Dropdown only, no add | Existing roles only | |
| Free text input | Text field, no FK enforcement | |

---

## Argument Metadata Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Out of scope for Phase 8 | Strictly people records only | ✓ (with note) |
| In scope — add case/argument editor | Edit case_name, docket_number, argued_date | |
| Minimal — edit argued_date only | Just the date | |

**Notes:** User chose out of scope, but noted this "needs to be in the next batch of work." Captured as deferred idea for Phase 9 or follow-on patch. The synthetic docket (`job-{id}`) created by Phase 7's job-driven ingest will need real values.

---

## Edit Form Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Sectioned single page | Three sections (Basic Info / Bio & Photo / Court Tenure) + single Save button | ✓ |
| All fields, no sections | Flat form | |
| Separate save per section | Each section has its own Save button | |

---

## Claude's Discretion

- Exact styling of the toggle switch
- Whether missing-fields badge chips are `<span>` tags or another element
- Whether tenure date inputs are `<input type="date">` or text fields
- Whether "Add new role" inline form appears below dropdown or as a small modal
- Exact wording of "Review people" link on the completed job page
- Whether participant list on job page shows a count header
- Exact amber color for missing-fields badge chips

## Deferred Ideas

- **Argument/case metadata editing** — editing title, docket_number, argued_date, case_name after Phase 7's synthetic ingest. Explicitly deferred to "the next batch of work" (Phase 9 candidate).
