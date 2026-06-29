# Phase 9: People Data Model Migration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-19
**Phase:** 9-people-data-model-migration
**Areas discussed:** full_name ↔ name parts relationship, Party affiliation storage, Edit form layout for new fields, Migration backfill strategy

---

## full_name ↔ name parts relationship

| Option | Description | Selected |
|--------|-------------|----------|
| Independent | full_name and name parts are completely separate; operator maintains both | |
| Auto-derive on save | Saving name parts overwrites full_name server-side when first_name is non-empty | ✓ |
| Preview only | Form shows a derived preview but operator confirms before overwriting full_name | |

**User's choice:** Auto-derive on save

---

| Option | Description | Selected |
|--------|-------------|----------|
| {first} {middle} {last} {suffix} | Western order; middle/suffix omitted when blank; parts stored separately | ✓ |
| {first} {last} only | Middle and suffix stored but never folded into full_name | |

**User's choice:** {first} {middle} {last} {suffix} — parts kept as separate columns for sorting/display

---

| Option | Description | Selected |
|--------|-------------|----------|
| Only when first_name is non-empty | full_name left unchanged if no name parts submitted | ✓ |
| Always | Derivation always fires, even if parts are blank | |

**User's choice:** Only when first_name is non-empty

---

| Option | Description | Selected |
|--------|-------------|----------|
| Phase 9 — add sort now | ORDER BY last_name NULLS LAST added while touching the directory query | ✓ |
| Defer to Phase 12 | Keep Phase 9 scope to data model and edit form only | |

**User's choice:** Phase 9 — add sort now
**Notes:** User explicitly asked for last-name sortability on the admin people directory.

---

| Option | Description | Selected |
|--------|-------------|----------|
| NULLS LAST | Records without last_name appear after all named records | ✓ |
| Fall back to full_name | Null last_name sorts by full_name instead | |

**User's choice:** NULLS LAST

---

| Option | Description | Selected |
|--------|-------------|----------|
| Show full_name as page title | e.g. "Edit: Amy Coney Barrett" | ✓ |
| Generic "Edit Person" | Static label, no dynamic title | |

**User's choice:** Show full_name as page title

---

## Party affiliation storage

| Option | Description | Selected |
|--------|-------------|----------|
| Free text VARCHAR | Operator types president's name; no constraint needed | ✓ |
| Constrained select | Dropdown of all US presidents | |

**User's choice:** Free text VARCHAR for appointing_president
**Notes:** User clarified mid-discussion that there is no party field on the person directly — both fields (appointed_by name + party) refer to the appointing president, not the Justice.

---

| Option | Description | Selected |
|--------|-------------|----------|
| VARCHAR with constrained frontend select | Plain VARCHAR in DB; <select> with fixed options in UI | ✓ |
| PostgreSQL enum | DB-level enforcement; ALTER TYPE needed to add parties | |
| Free text | No constraint; risk of inconsistent values | |

**User's choice:** VARCHAR with constrained frontend select

---

| Option | Description | Selected |
|--------|-------------|----------|
| Democratic, Republican, Whig, Federalist, Democratic-Republican, Independent | Full historical coverage | ✓ |
| Democratic, Republican only | Modern parties only | |

**User's choice:** Full historical list (6 options)

---

## Edit form layout for new fields

| Option | Description | Selected |
|--------|-------------|----------|
| Expand Basic Info — name parts below full_name | No new section; grows existing section | ✓ |
| New "Name Details" section | 4th section between Basic Info and Bio & Photo | |
| Replace full_name with parts | Remove full_name input; parts are the only name inputs | |

**User's choice:** Expand Basic Info

---

| Option | Description | Selected |
|--------|-------------|----------|
| Keep full_name as editable field, name parts below it | Both inputs always active; server derives when first_name non-empty | ✓ |
| full_name read-only when parts are filled | Read-only derived display when first/last set; editable otherwise | |
| full_name hidden once parts filled | full_name input disappears when first_name non-empty | |

**User's choice:** Keep full_name as editable field alongside name parts

---

| Option | Description | Selected |
|--------|-------------|----------|
| New "Appointment" section after Court Tenure | 4th section; form order: Basic Info → Bio & Photo → Court Tenure → Appointment | ✓ |
| Inside Basic Info | Appointment fields in expanded Basic Info section | |
| Alongside Court Tenure | Merged "Justice Details" section | |

**User's choice:** New Appointment section after Court Tenure

---

## Migration backfill strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Leave all new fields NULL — operator fills as needed | Zero risk; existing records unaffected | ✓ |
| Best-effort parse full_name into parts | Attempt to split existing names; risky for complex names | |

**User's choice:** Leave NULL — no backfill

---

| Option | Description | Selected |
|--------|-------------|----------|
| 0006_add_structured_name_fields.py | Continues sequence from Phase 8 migration 0005 | ✓ |
| Check DB first | Verify latest migration number in environment | |

**User's choice:** 0006 confirmed

---

## Claude's Discretion

- Responsive layout for the 4-input name parts row (column widths, breakpoints)
- Whether name_suffix is a free-text input or a select with common suffixes (Jr., Sr., II, III)
- Exact wording of the Appointment section header
- Whether a note ("Leave blank for advocates") appears in the Appointment section
- Amber chip colors and styling details (follow Phase 8 dark theme tokens)

## Deferred Ideas

- Public display of name parts and appointing president → Phase 14 (Speaker Popover Card)
- Advocate firm/organization affiliation field → v1.3+ (ADV-01, explicitly deferred)
- Bulk backfill of name parts from full_name values → one-off data task, out of scope
