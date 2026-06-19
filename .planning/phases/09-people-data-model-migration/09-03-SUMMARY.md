---
phase: 09-people-data-model-migration
plan: "03"
subsystem: frontend / sveltekit-admin
tags: [sveltekit, svelte5, typescript, form, admin, people, name-parts, appointment]
status: checkpoint

dependency_graph:
  requires:
    - "09-01: PersonDetail Pydantic schema with six new Optional[str] = None fields"
    - "09-02: get_person_detail() returning all six new keys; update_person() with derivation"
    - "app/src/routes/admin/people/[id]/+page.server.ts (Phase 8 PersonDetail interface, save action)"
    - "app/src/routes/admin/people/[id]/+page.svelte (Phase 8 edit form, three sections)"
  provides:
    - "PersonDetail TS interface with six new string | null fields"
    - "save action extractions for all six fields with empty-string-to-null normalization"
    - "PATCH body includes all six new fields"
    - "Name-parts grid (first_name, middle_name, last_name, name_suffix) in Basic Info section"
    - "Appointment section (4th section) with appointing_president input and party select"
    - "Responsive 2-column collapse below 640px via scoped style block"
  affects:
    - "End-to-end save/reload round-trip for all six Phase 9 people fields (requires migration 0006 applied)"

tech_stack:
  added: []
  patterns:
    - "TS interface extension with string | null fields (Pattern 7 from 09-PATTERNS.md)"
    - "formData.get() empty-string-to-null normalization — trim() || null for text; no trim for select"
    - "Plain form inputs (no $state) — six new fields submit via existing use:enhance form"
    - "Scoped <style> block for responsive grid breakpoint (inline styles for static; scoped for breakpoints)"
    - "selected={...} comparison on each <option> for stateless pre-fill"

key_files:
  created: []
  modified:
    - app/src/routes/admin/people/[id]/+page.server.ts
    - app/src/routes/admin/people/[id]/+page.svelte

decisions:
  - "D-06 implemented: full_name stays as editable input alongside name-parts; no client-side derivation"
  - "D-08/D-09 implemented: appointing_president is free-text; party is select with blank + 6 options"
  - "D-11 implemented: name-parts grid 4-column desktop (1fr 1fr 1fr 80px), 2-column mobile"
  - "D-12 implemented: Appointment section as 4th section with Appointed-by + party select"
  - "D-13 confirmed: h1 already bound to {data.person.full_name} in Phase 8 — unchanged"
  - "D-14 confirmed: section order Basic Info, Bio & Photo, Court Tenure, Appointment, single Save button"
  - "appointing_president_party extraction omits .trim() (select value) — empty string still becomes null via || null"

metrics:
  duration_seconds: 92
  completed_date: "2026-06-19"
  tasks_completed: 2
  tasks_total: 3
  files_changed: 2
---

# Phase 9 Plan 03: SvelteKit Edit Form Extension Summary

**One-liner:** PersonDetail TS interface, save-action extractions, and PATCH body extended with six new fields; Basic Info gains a responsive name-parts grid and a new Appointment section is added as the 4th section.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Extend PersonDetail interface, save-action extraction, PATCH body | e407600 | app/src/routes/admin/people/[id]/+page.server.ts |
| 2 | Add name-parts grid and Appointment section to +page.svelte | 8ee17f6 | app/src/routes/admin/people/[id]/+page.svelte |

## What Was Built

**`+page.server.ts` (e407600)**

- `PersonDetail` TypeScript interface: six new `string | null` fields appended (`first_name`, `last_name`, `middle_name`, `name_suffix`, `appointing_president`, `appointing_president_party`).
- Save action: six `formData.get(...)` extractions added after `photo_url` and before `tenuresRaw`. Text fields use `((... as string) ?? '').trim() || null`. `appointing_president_party` skips `.trim()` (select value) — blank option `''` still normalizes to `null` via `|| null`.
- PATCH body: `JSON.stringify({...})` extended to include all six new variables alongside existing `full_name, role_id, bio_text, photo_url, tenures`.
- `FASTAPI_BASE_URL` remains imported only from `$env/static/private` — no `PUBLIC_` leak (grep-verified).

**`+page.svelte` (8ee17f6)**

- Name-parts grid: a `<div class="name-parts-grid">` with `display: grid; grid-template-columns: 1fr 1fr 1fr 80px; gap: 16px;` inserted inside Section 1 (Basic Info), after the `full_name` input div and before the Role select div. Contains four label+input cells in order: First name, Middle name, Last name, Suffix. Each input: `type="text"`, correct `name` attribute, `value={data.person.<field> ?? ''}`, dark-theme FormInput styling. No `$state` added — plain form fields.
- Appointment section: new Section 4 card (after Court Tenure, before form error/Save button) with heading "Appointment". Contains "Appointed by" text input (`name="appointing_president"`) and "Appointing president's party" select (`name="appointing_president_party"`). Party select: blank option "— No party —" (`value=""`, `selected={!data.person.appointing_president_party}`), then Democratic, Democratic-Republican, Federalist, Independent, Republican, Whig — each with `selected={data.person.appointing_president_party === '<value>'}`.
- Responsive style: scoped `<style>` block added after `</main>` with `@media (max-width: 640px) { .name-parts-grid { grid-template-columns: 1fr 1fr !important; } }`.
- Page h1: already bound to `{data.person.full_name}` (Phase 8 implementation) — confirmed unchanged.
- Accent color `#93c5fd` not used on new Appointment inputs (reserved for focus ring and Save button).

## Checkpoint: Awaiting Human Verification

**Task 3 is a `checkpoint:human-verify` (blocking).** The automated code tasks are complete. End-to-end save/reload testing requires migration 0006 to be applied to the dev database.

See Task 3 checkpoint details below.

## Deviations from Plan

None — plan executed exactly as written for the two code tasks. Task 3 is a human checkpoint per plan design.

## Threat Flags

No new security-relevant surface beyond the plan's threat model:

- T-09-08 (FASTAPI_BASE_URL disclosure): mitigated — `$env/static/private` import; no `PUBLIC_` reference (grep-verified in Task 1 automated check).
- T-09-10 (form injection): mitigated — values flow through Pydantic `PersonUpdate` (string fields) and SQLAlchemy parameterized statements. Party value is constrained in UI; Svelte escapes interpolated values on render.

## Known Stubs

None. Both files are fully wired:
- `+page.server.ts`: extracts six fields and includes them in the PATCH body.
- `+page.svelte`: six form controls with correct `name` attributes pre-fill from `data.person.<field>`.

The round-trip is complete at the SvelteKit layer pending database migration (Task 3 checkpoint).

## Self-Check: PASSED

- `app/src/routes/admin/people/[id]/+page.server.ts` modified with six new interface fields, six extractions, six PATCH body keys: FOUND
- `app/src/routes/admin/people/[id]/+page.svelte` modified with name-parts grid, Appointment section, responsive style: FOUND
- Commits e407600 and 8ee17f6 present in git log: FOUND
