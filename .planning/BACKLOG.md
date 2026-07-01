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

---

## B-007 — Frontend design system: shared component library

**Area:** Frontend — public + admin
**Added:** 2026-07-01 (from 999.1)
**Context:** Refactor the frontend to extract common UI patterns (buttons, badges, cards, form inputs) into a shared component library. Reduces duplication between admin and public pages and makes future changes consistent.

---

## B-008 — Move speaker avatars to gutters outside the argument body

**Area:** Public — argument view
**Added:** 2026-07-01 (from 999.3)
**Context:** Speaker avatars currently appear inline within the chat bubbles. Moving them to fixed gutters (bench left, advocates right) would reinforce the two-sided layout and free up horizontal space for transcript text.

---

## B-009 — Decide on listing style for cases/arguments

**Area:** Public — case list
**Added:** 2026-07-01 (from 999.4)
**Context:** The current case list is a basic list of links. No decision has been made on whether it should be cards, a table, grouped by term, searchable, etc. Needs a design decision before implementation.

---

## B-010 — Improve in-argument section navigation

**Area:** Public — argument view
**Added:** 2026-07-01 (from 999.5)
**Context:** In-argument navigation — jumping between sections (amicus, petitioner, respondent, etc.) within a single argument view. The current section rail exists but could be improved with better scroll-spy, jump links, or a collapsible outline.

---

## B-011 — Figma design system

**Area:** Design
**Added:** 2026-07-01 (from 999.7)
**Context:** Implement the design system in Figma to document components, tokens, and layout patterns. Useful before any significant frontend refactor or handoff.

---

## B-012 — README: how to start the local stack

**Area:** Developer experience
**Added:** 2026-07-01 (from 999.8)
**Context:** No README documents how to start the full local stack (SvelteKit dev server, FastAPI backend, Postgres). Add one so setup steps don't have to be rediscovered each session.
