---
phase: 09-people-data-model-migration
fixed_at: 2026-06-19T18:30:00Z
review_path: .planning/phases/09-people-data-model-migration/09-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 9: Code Review Fix Report

**Fixed at:** 2026-06-19T18:30:00Z
**Source review:** .planning/phases/09-people-data-model-migration/09-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 6 (2 Critical, 4 Warning)
- Fixed: 6
- Skipped: 0

## Fixed Issues

### CR-01: Sentinel role option can silently erase an existing role on save

**Files modified:** `app/src/routes/admin/people/[id]/+page.server.ts`, `app/src/routes/admin/people/[id]/+page.svelte`
**Commit:** 7320c37
**Applied fix:**
- Added a NaN guard in `+page.server.ts` after `parseInt(role_id_raw, 10)`: if `role_id_raw` is truthy and `role_id` is NaN (i.e., the sentinel string was submitted), returns a `fail(400)` with a descriptive error before any PATCH is sent.
- In `+page.svelte`: added `roleIdBeforeSentinel` state that records the previous `selectedRoleId` when the sentinel option is chosen; added a `cancelAddRole()` function that restores it and hides the inline form; added a Cancel button in the inline role form that calls `cancelAddRole()`; switched the role `<select>` from one-way `value={selectedRoleId}` to two-way `bind:value={selectedRoleId}` so state mutations (including cancel restore) reflect back to the DOM immediately; removed the now-redundant per-option `selected={...}` attributes.

---

### CR-02: `update_person` applies `role_id` unconditionally — absent field indistinguishable from explicit null

**Files modified:** `api/services/admin_people.py`
**Commit:** 64d9d00
**Applied fix:** Wrapped `person.role_id = body.role_id`, `person.bio_text = ...`, and `person.photo_url = ...` assignments in `if "field_name" in body.model_fields_set:` guards. Uses Pydantic v2's `model_fields_set` to distinguish a field that was explicitly included in the JSON body (even as null) from a field that was absent (which defaults to None). Prevents a partial PATCH that omits `role_id` from silently NULLing out an existing role assignment.

---

### WR-01: `create_role` TOCTOU race produces unhandled `IntegrityError` (500)

**Files modified:** `api/services/admin_people.py`
**Commit:** 2af7d3f
**Applied fix:** Removed the select-before-insert pre-check pattern. Replaced with a try/except block that inserts immediately: if a concurrent request races and triggers an `IntegrityError` on the unique constraint, rolls back the transaction and re-queries for the existing row. Added `from sqlalchemy.exc import IntegrityError` import. This eliminates the 500 response on concurrent role creation.

---

### WR-02: `_derive_full_name` called with raw body values after normalization

**Files modified:** `api/services/admin_people.py`
**Commit:** 51d4424
**Applied fix:** Changed the `_derive_full_name` call in `update_person` to pass `person.middle_name` and `person.name_suffix` (already normalized to None when blank, two lines above) instead of `body.middle_name` and `body.name_suffix` (the raw un-normalized values). The code is now internally consistent: normalization and derivation both operate on the same canonical values.

---

### WR-03: `list_people` sort behavior contradicts docstring; all legacy rows sorted to bottom

**Files modified:** `api/services/admin_people.py`
**Commit:** 03c58e9
**Applied fix:** Replaced the two-key `last_name NULLS LAST, full_name ASC` sort with `COALESCE(last_name, full_name) ASC`. Legacy people whose `last_name` is NULL are now sorted by `full_name` as a fallback, keeping the directory coherent rather than pushing all pre-Phase-9 rows to the bottom. Added `func as sqlfunc` to the SQLAlchemy import. Updated the docstring to document the sort key accurately.

---

### WR-04: `appointing_president_party` not `.trim()`-ed in the server action

**Files modified:** `app/src/routes/admin/people/[id]/+page.server.ts`
**Commit:** f5473ed
**Applied fix:** Added `.trim()` to the `appointing_president_party` extraction in the `save` action, making it consistent with every other field. The field comes from a `<select>` so whitespace is unlikely in practice, but consistency prevents silent whitespace storage from non-browser clients or future input type changes.

---

_Fixed: 2026-06-19T18:30:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
