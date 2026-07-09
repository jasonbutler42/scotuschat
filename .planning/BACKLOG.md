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

---

## B-013 — Bulk-import historical justices from CSV

**Area:** Admin — People directory (`/admin/people`) — feeds Phase 27
**Added:** 2026-07-07
**Context:** Operator currently has to manually enter every historical Supreme Court justice one at a time in the People admin screen. Jason already has a CSV covering all historical justices. Add an import path (upload + parse + create/update `Person` rows with `is_justice=true`, tenure/appointment data) so the full bench roster can be seeded in one operation instead of by hand. Needs a decision on dedup behavior against existing entries and which CSV columns map to which fields. Operator does not need this as a standing feature, just at the beginning of the project. This could be done without an user interface and should persist for future plans. We currently have seeded the database with the current justices, this would be similar to what we are doing now.

---

## B-014 — 1 click to copy extracted values design pattern

**Area:** Admin — Pipeline details (`/admin/pipeline/[job_id]`)
**Added:** 2026-07-07
**Context:** Operator wants to be able to click on the extracted value and have it copied to their clipboard so they can easily paste it into the relevant fields. Each individual value needs to work like this, including the extracted docket number(s). This pattern should operate the same wherever it is implemented -- it should carry through the ability to copy to clipboard on the pipeline run as well as the argument editor pages. If there was no extracted value and it's showing N/A, then the copy functionality should not be enabled; there's no need for it to work if nothing was extracted. What is the operator going to copy? NOTHING?! (that's sarcasm). The same component should be used for this functionality throughout the site so it's consistent. 

---

## B-015 — New data for Bench people

**Area:** Bench popover detail cards
**Added:** 2026-07-07
**Context:** When someone is viewing an argument and clicks on a Justice's avatar, they should see information that gives context about them and to the case. Some data is persistent and doesn't change from case to case. At minimum this includes:
- Their name
- a photo of them
- birthdate
- death date
- a list of their tenures with 
  - start and end dates
  - which President appointed them to that tenure
  - what that President's party affiliation was
  - why they left that tenure (death, retirement, promotion)

Other information is case specific. We need to explore this further to see what other context we can give visitors that will help them understand where a justice is coming from. At minimum I want to explore:
- Their age at the time of the argument
- How long had they been in their position
  - maybe a count of cases heard in that role (objective numbers)
  - maybe a visual indicator that shows where the argument falls on their tenure(s) (subjective length of time)

The risk that needs to be explored, too, is around bias. I want to give visitors information in the least biased way possible.

---

## B-016 — `rerun_job` never spawns ingest for locally-uploaded jobs (no DO Spaces configured)

**Area:** Admin — Pipeline jobs (`api/routers/admin.py`, `api/services/admin_jobs.py`) — Phase 24 scope
**Added:** 2026-07-08 (from 26-REVIEW.md CR-01)
**Context:** `create_job`'s upload path stores the PDF at `data/uploads/{job.id}.pdf` and sets neither `spaces_key` nor `pdf_url` when `settings.do_spaces_bucket` is falsy (local/dev mode, no DO Spaces configured). `rerun_job` copies `pdf_url`/`spaces_key`/`original_filename`/`source_dockets` onto the new job, but the rerun endpoint (`api/routers/admin.py:1042-1076`) only branches on `spaces_key` or `pdf_url` — there is no `else` branch for a local-disk-backed original, so no ingest subprocess is ever spawned for the rerun. The endpoint still returns `202` with a fresh `PENDING` job, giving the operator every indication the rerun started, but the job sits at `PENDING/INGEST` forever with no error surfaced. Confirmed unresolved across two review passes (pre- and post-gap-closure) — not touched by any Phase 26 commits. Fix: persist the resolved local file path on `AdminJob` at creation time and add a third rerun branch that re-spawns ingest with `--local-file`, or at minimum raise a `ValueError` (422) instead of silently creating a job that can never progress.

---

## B-017 — Blank `case_name`/`docket_number` can be saved via admin edit, corrupting slug and dedup-key data

**Area:** Admin — Argument edit (`api/schemas/admin_arguments.py`, `api/services/admin_arguments.py`, `app/src/routes/admin/arguments/[id]/+page.svelte`)
**Added:** 2026-07-08 (from 26-REVIEW.md CR-02)
**Context:** `ArgumentUpdate.case_name`/`.docket_number` are `Optional[str] = None` with no non-empty validation; `update_argument` treats "not None" as "provided," not "non-empty." The edit form's `?/save` action always sends a trimmed string (never `undefined`) and the `<input>` elements have no `required` attribute. If an operator clears either field and clicks Save, the write proceeds: for a `DRAFT` argument, `_derive_slug("")` returns `""`, corrupting the case's public URL slug; for any status, `docket_number`/`docket_number_norm` can be wiped to `""`, breaking dedup semantics. Same "not-None treated as provided" gap exists in the sibling `update_argument_metadata` (`case_name` at `api/services/admin_arguments.py:781-795`, `source_docket` at `763-764`). Fix: add a Pydantic `field_validator` rejecting blank/whitespace-only values on `ArgumentUpdate` and `MetadataUpdate`, plus `required` on both `<input>` elements as defense-in-depth.

---

## B-018 — `update_argument_metadata` has no guard against the `(source_docket, question_number)` unique constraint

**Area:** Admin — Argument metadata (`api/services/admin_arguments.py`)
**Added:** 2026-07-08 (from 26-REVIEW.md CR-03)
**Context:** `update_argument_metadata` writes `source_docket`/`question_number` without first checking whether another `Argument` row already holds that combination. Introduced in Phase 19 (`a9cbf218`), untouched by Phase 26. Saving a metadata edit that collides with an existing row will raise an unhandled `IntegrityError` (500) instead of a clean, user-facing validation error. Fix: add a pre-write existence check (or catch `IntegrityError` and map it to a 409/422 with a clear message) before committing the update.

---

## B-019 — Rethink Full Name vs. name-part fields in the people editor

**Area:** Admin — People editor (`app/src/routes/admin/people/[id]/+page.svelte`, `/new`)
**Added:** 2026-07-09 (from Phase 27 UAT)
**Context:** Jason expected that filling in only the component name fields (first/last/middle/suffix) without Full Name would auto-backfill Full Name on save — instead, Full Name is currently required standalone. Proposed direction: stop making Full Name operator-editable at all, and derive it entirely from the component fields — "We'd have to adjust the way parsing works but that feels like the better way to go." Needs a design decision on exactly how derivation should work (ordering, suffix placement, punctuation) and what changes on the pipeline/parsing side before this can be scoped. Related to the real bug tracked as a Phase 27 UAT gap (create route silently discards name-part fields when Full Name is also filled) — that bug is being fixed now; this backlog item is the broader "should Full Name exist as a separate editable field at all" question, deferred.

---

## B-020 — Represent tenure Seat as a Chief/Associate toggle instead of free text

**Area:** Admin — People editor, Tenure Period sub-card (`app/src/routes/admin/people/[id]/+page.svelte`)
**Added:** 2026-07-09 (from Phase 27 UAT)
**Context:** During Phase 27 UAT, Jason asked for the tenure-row Seat field (currently free-text, restored during Phase 27 verification per PEDIT-09) to become the same segmented-toggle component used for the Bench/Advocate choice, since for a Justice it's really just Chief or Associate. Deferred rather than fixed immediately (Jason offered this exit himself) because real historical `court_tenures.seat` data includes specific numbered seats (e.g. "Associate Justice Seat 3"), not just a binary Chief/Associate split — collapsing to a 2-option toggle is a genuine data-model simplification that needs a decision on whether the numbered-seat detail is dropped, kept as a secondary field, or reconciled some other way, plus a migration/backfill pass over existing rows. Companion to B-013 (bulk CSV import of historical justices), since both touch how much seat-numbering granularity the system needs to preserve.