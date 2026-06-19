---
phase: 09-people-data-model-migration
reviewed: 2026-06-19T12:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - alembic/versions/0006_add_structured_name_fields.py
  - api/models/models.py
  - api/schemas/admin_people.py
  - api/services/admin_people.py
  - api/tests/test_admin_people_schemas_service.py
  - app/src/routes/admin/people/[id]/+page.server.ts
  - app/src/routes/admin/people/[id]/+page.svelte
findings:
  critical: 2
  warning: 4
  info: 3
  total: 9
status: issues_found
---

# Phase 9: Code Review Report

**Reviewed:** 2026-06-19T12:00:00Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Phase 9 adds six nullable columns to the `people` table (structured name parts + appointment fields), extends the admin People Editor form, and plumbs the new fields through the Pydantic schemas, service layer, and SvelteKit page. The Alembic migration and ORM model additions are clean and follow existing patterns. The Pydantic schema layer is correct. The most serious issues are a data-loss path in the service's unconditional `role_id` assignment and a compounding bug in the frontend where the sentinel role option can cause `NaN` to be serialized as `null`, silently clearing an existing role on save. There are also a TOCTOU race in `create_role`, a derivation inconsistency using raw vs. normalized values, and a sort behavior mismatch vs. documentation.

---

## Critical Issues

### CR-01: Sentinel role option can silently erase an existing role on save

**File:** `app/src/routes/admin/people/[id]/+page.svelte:235` and `app/src/routes/admin/people/[id]/+page.server.ts:103`

**Issue:** The role `<select>` contains a sentinel option with `value="__add_new_role__"` (svelte line 235). The `handleRoleChange` handler (svelte lines 47-55) sets `showAddRoleForm = true` when the sentinel is chosen but does **not** update `selectedRoleId` away from the sentinel. If the user selects "Add new role", dismisses the inline form without completing it, and then clicks "Save changes", the outer form submits `role_id=__add_new_role__`.

In `+page.server.ts` line 103:
```ts
const role_id = role_id_raw ? parseInt(role_id_raw, 10) : null;
```
`parseInt('__add_new_role__', 10)` returns `NaN`. `JSON.stringify({ role_id: NaN })` serializes `NaN` as `null` per the JSON spec. The API receives `role_id: null`. In the service (see CR-02), `role_id` is applied unconditionally, so the person's role is silently cleared. No error surfaces to the user.

**Fix:** Add a NaN guard after `parseInt` in `+page.server.ts` and block save while the sentinel is active:

```ts
// +page.server.ts — after line 103
const role_id = role_id_raw ? parseInt(role_id_raw, 10) : null;
if (role_id_raw && (isNaN(role_id as number))) {
    return fail(400, { error: 'Please select a valid role or complete the new-role form before saving.' });
}
```

Additionally, disable the save button in the Svelte component while `showAddRoleForm` is true, or reset `selectedRoleId` to the previously held value when the inline form is dismissed without completing it.

---

### CR-02: `update_person` applies `role_id` unconditionally — absent field indistinguishable from explicit null, causes data loss

**File:** `api/services/admin_people.py:222`

**Issue:** Line 222:
```python
person.role_id = body.role_id
```
executes unconditionally for every PATCH request. `PersonUpdate.role_id` defaults to `None` (schema line 84). Any PATCH that omits `role_id` from the JSON body will have `body.role_id == None`, and the service will write `NULL` to `person.role_id`, silently removing an existing role assignment.

The comment says "role_id may be explicitly set to None (remove role) or a new id" but the schema makes `None` the default for an *absent* field, so absent and explicit-null are indistinguishable at this layer. This is a data-loss footgun for any non-UI caller that issues a partial PATCH omitting `role_id`. It also compounds CR-01: by the time the NaN-serialized `null` arrives here, there is no way to distinguish it from an intentional role removal.

**Fix:** Use Pydantic v2's `model_fields_set` to distinguish absent from explicit-null:
```python
# Only write role_id when the client explicitly included it in the JSON body
if "role_id" in body.model_fields_set:
    person.role_id = body.role_id
```
Apply the same guard to `bio_text` (line 224) and `photo_url` (line 225) for consistency — those fields share the same ambiguity.

---

## Warnings

### WR-01: `create_role` TOCTOU race produces unhandled `IntegrityError` (500)

**File:** `api/services/admin_people.py:262-270`

**Issue:** The find-or-create pattern checks for existence then inserts:
```python
result = await db.execute(select(Role).where(Role.name == name))
role = result.scalar_one_or_none()
if role is not None:
    return {"id": role.id, "name": role.name}
role = Role(name=name)
db.add(role)
await db.flush()   # raises IntegrityError if concurrent request already inserted
```
Two concurrent `createRole` requests for the same name can both pass the `None` guard and both reach `db.flush()`. The second flush raises `sqlalchemy.exc.IntegrityError` from the unique constraint on `roles.name`. This exception is not caught anywhere in the service or (based on the reviewed files) the router, and propagates as a 500.

**Fix:**
```python
from sqlalchemy.exc import IntegrityError

# Remove the pre-check; go straight to insert and handle the race
try:
    role = Role(name=name)
    db.add(role)
    await db.flush()
    await db.commit()
    await db.refresh(role)
    return {"id": role.id, "name": role.name}
except IntegrityError:
    await db.rollback()
    result = await db.execute(select(Role).where(Role.name == name))
    existing = result.scalar_one()
    return {"id": existing.id, "name": existing.name}
```

---

### WR-02: `_derive_full_name` called with raw body values after normalization — inconsistency risks silent regression

**File:** `api/services/admin_people.py:239-245`

**Issue:** Lines 229-234 normalize the name parts from `body.*` into `person.*` (empty string → None). The derivation block at lines 239-245 then passes `body.middle_name` and `body.name_suffix` — the raw, un-normalized values — to `_derive_full_name`:

```python
person.first_name  = body.first_name  if body.first_name  else None  # line 229
person.middle_name = body.middle_name if body.middle_name else None  # line 231
person.name_suffix = body.name_suffix if body.name_suffix else None  # line 232

if body.first_name and body.last_name:
    person.full_name = _derive_full_name(
        body.first_name,
        body.middle_name,   # raw value — not person.middle_name
        body.last_name,
        body.name_suffix,   # raw value — not person.name_suffix
    )
```

`_derive_full_name` happens to filter falsy strings in its `" ".join(...)` comprehension, so an empty-string middle or suffix is silently dropped and the output is correct today. However the code is internally inconsistent: `person.middle_name` and `person.name_suffix` are already set to the canonical normalized values at that point, but the derivation bypasses them. Any future change to `_derive_full_name` that stops filtering falsy parts would silently produce names like `"John  Roberts"` (double-space from empty middle).

**Fix:** Pass the already-normalized instance attributes to `_derive_full_name`:
```python
if body.first_name and body.last_name:
    person.full_name = _derive_full_name(
        body.first_name,
        person.middle_name,   # already None if blank
        body.last_name,
        person.name_suffix,   # already None if blank
    )
```

---

### WR-03: `list_people` sort behavior contradicts docstring; all legacy rows sorted to bottom

**File:** `api/services/admin_people.py:114-126`

**Issue:** The docstring (line 115) says the function returns people "sorted by `full_name`". The actual query (line 126) sorts by `last_name NULLS LAST, full_name ASC`:
```python
.order_by(Person.last_name.nulls_last(), Person.full_name.asc())
```
Since all pre-existing people (created before Phase 9) have `last_name = NULL` (the new column defaults to NULL per the migration), they all sort to the bottom of the directory listing, ordered only by `full_name` among themselves. New people with `last_name` set will appear at the top. This creates a split directory where pre-Phase-9 people fall to the bottom until an operator manually fills in their `last_name`. The docstring hides this behavior entirely.

This is a UX correctness issue: the directory will look broken to any operator who views it before all rows are back-filled.

**Fix:** Either:
1. Accept the behavior and update the docstring to document it clearly: "sorted by `last_name` (nulls last), then `full_name` within each group".
2. Or use `COALESCE(last_name, full_name)` to sort all rows on a consistent key regardless of whether `last_name` is populated:
```python
from sqlalchemy import func as sqlfunc
.order_by(sqlfunc.coalesce(Person.last_name, Person.full_name).asc())
```

---

### WR-04: `appointing_president_party` not `.trim()`-ed in the server action

**File:** `app/src/routes/admin/people/[id]/+page.server.ts:111`

**Issue:** Every other text field in the `save` action is trimmed before null-coalescing. `appointing_president_party` is the only exception:
```ts
// line 111 — missing .trim()
const appointing_president_party = ((formData.get('appointing_president_party') as string) ?? '') || null;

// All other fields for comparison:
const appointing_president = ((formData.get('appointing_president') as string) ?? '').trim() || null;
```
The value comes from a `<select>` so whitespace is unlikely in practice, but the inconsistency means any future change to a free-text input, a test injecting a padded value, or a non-browser client would silently store a whitespace-padded party string that would not match equality checks.

**Fix:**
```ts
const appointing_president_party = ((formData.get('appointing_president_party') as string) ?? '').trim() || null;
```

---

## Info

### IN-01: Phase 9 fields absent from `PersonUpdate` and `PersonDetail` test coverage

**File:** `api/tests/test_admin_people_schemas_service.py:141-155`

**Issue:** `test_person_update_with_all_fields` (line 141) instantiates `PersonUpdate` with `full_name`, `role_id`, `bio_text`, `photo_url`, and `tenures` but none of the six Phase 9 fields. `test_person_detail_shape` (line 225) similarly omits them. There is no test confirming the new fields are accepted, round-tripped, or accessible on the schema objects. There is also no test covering the interaction between an explicit `full_name` in `PersonUpdate` and Phase 9 name parts (the derivation override path in `update_person` lines 239-245).

**Fix:** Extend both tests to include Phase 9 fields, and add a test for `_derive_full_name` being skipped when only `first_name` is provided without `last_name`.

---

### IN-02: `use:enhance` save callback has a dead branch — both arms call `update()` identically

**File:** `app/src/routes/admin/people/[id]/+page.svelte:110-117`

**Issue:**
```ts
return async ({ result, update }) => {
    saveSubmitting = false;
    if (result.type === 'redirect') {
        await update();
    } else {
        await update();
    }
};
```
Both branches call `await update()` with no arguments. Additionally, SvelteKit's `use:enhance` intercepts `redirect` results and navigates automatically before the callback fires, making the `'redirect'` branch unreachable. The conditional adds no logic and will mislead future readers.

**Fix:**
```ts
return async ({ update }) => {
    saveSubmitting = false;
    await update();
};
```

---

### IN-03: `selectedRoleId` state update after `createRole` may not reflect in the controlled `<select>` (one-way binding)

**File:** `app/src/routes/admin/people/[id]/+page.svelte:34-36, 252-259`

**Issue:** The role `<select>` uses a non-bound `value` prop:
```svelte
<select ... value={selectedRoleId} onchange={handleRoleChange}>
```
In Svelte 5 Runes, `value={...}` on a `<select>` is a one-way binding — it sets the initial DOM value but does not reflect subsequent JS mutations back to the DOM. After `createRole` succeeds (line 259), the callback sets `selectedRoleId = String(data.role.id)`. This state mutation may not update the visible selected option in the `<select>` element because there is no reactive two-way binding.

In Svelte 5, controlling a `<select>` value from JS requires `bind:value` for the DOM to stay in sync with the reactive variable.

**Fix:** Replace `value={selectedRoleId}` with `bind:value={selectedRoleId}` on the role `<select>` element (line 224). Remove the now-redundant manual `selected={...}` attribute on each `<option>` child — `bind:value` manages option selection automatically.

---

_Reviewed: 2026-06-19T12:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
