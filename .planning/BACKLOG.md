# Backlog

Unscheduled items for future phases.

---

## B-001 — Make the toggle switch the way Jason wants it

**Area:** Admin — People directory (`/admin/people`)
**Added:** 2026-06-18
**Context:** The toggle's functional behavior works (navigates to `?incomplete=1`, filters correctly), but the visual appearance of the switch when toggled on is broken. Details TBD by Jason.

---

## B-002 — Link participant names on job detail page to their edit entries

**Area:** Admin — Pipeline job detail (`/admin/pipeline/[id]`)
**Added:** 2026-06-18
**Context:** The resolved participants section lists people by name but the names are plain text. Each participant name should be a link to their people editor entry at `/admin/people/[id]` so the operator can navigate directly from a job result to the person's edit form.

---

## B-005 — Animate bench section show/hide when toggling Is Justice

**Area:** Admin — People editor (`/admin/people/[id]`)
**Added:** 2026-06-29
**Context:** The Role, Court Tenure, and Appointment sections currently snap in/out of existence when the Is Justice checkbox is toggled. A smooth transition (e.g., fade or slide) would feel less jarring.

---

## B-004 — Unify Role and Court Tenure Seat into a context-aware role interface

**Area:** Admin — People editor (`/admin/people/[id]`)
**Added:** 2026-06-29
**Context:** The current design has a "Role" dropdown in Basic Info and a separate "Seat" field under Court Tenure — these overlap conceptually. Proposed: collapse into a single role interface that adapts by person type. Justices get an enumerated Seat picker (Justice-specific roles). Advocates need no role field at all. May be partially or fully addressed by an upcoming phase — keep in backlog and delete if redundant.

---

## B-003 — Move Justice-only fields to a dedicated card with Is Justice checkbox

**Area:** Admin — People editor (`/admin/people/[id]`)
**Added:** 2026-06-29
**Context:** Currently the Is Justice checkbox is in Basic Info and the Justice-only sections (Role, Court Tenure, Appointment) appear below inline. UX would be cleaner with a dedicated "Justice Details" card that contains the Is Justice checkbox plus the conditional bench sections, keeping Basic Info clean.

---

## B-006 — Pipeline list badge: show active step alongside run status

**Area:** Admin — Pipeline list (`/admin/pipeline`)
**Added:** 2026-07-01
**Context:** The status badge on the pipeline list page shows only the run-level state (e.g. "Running"). While a run is in progress, the badge should also show the current step so the operator knows where in the pipeline it is — format: "Parse | Failed" or "Resolve | Running". Once the run reaches a terminal state (Completed, Failed, Needs Review), the step suffix is dropped and just the run status is shown.
