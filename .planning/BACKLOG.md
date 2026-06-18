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
