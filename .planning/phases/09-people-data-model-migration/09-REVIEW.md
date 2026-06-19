---
phase: 09-people-data-model-migration
reviewed: 2026-06-19T00:00:00Z
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
  warning: 3
  info: 2
  total: 7
status: issues_found
---

# Phase 9: Code Review Report

**Reviewed:** 2026-06-19T00:00:00Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Phase 9 adds six nullable columns to the `people` table (structured name parts + appointment fields), extends the admin People Editor form, and plumbs the new fields through the Pydantic schemas, service layer, and SvelteKit page. The migration and ORM model are clean. The schema layer is well-structured. The most serious issues are in the interaction between the frontend form state and the backend service: a sentinel value can silently erase a person's role, and an unconditional `role_id` assignment in the service breaks the PATCH semantics for any non-UI caller. There are also meaningful test coverage gaps for the new Phase 9 fields.

---

## Critical Issues

### CR-01: Sentinel role value submits as `null`, silently clearing an existing role

**File:** `app/src/routes/admin/people/[id]/+page.svelte:235` and `app/src/routes/admin/people/[id]/+page.server.ts:103`

**Issue:** The role `<select>` contains a sentinel option with `value="__add_new_role__"` (line 235 of the Svelte file). The `handleRoleChange` handler (lines 47-55) sets `showAddRoleForm = true` but does NOT update `selectedRoleId` away from the sentinel. The select element's actual submitted form value remains `__add_new_role__`. If the user selects "＋ Add new role", does not complete the inline role creation form, and then clicks "Save changes", the outer save form submits `role_id=__add_new_role__`.

In `+page.server.ts` line 103:
```ts
const role_id = role_id_raw ? parseInt(role_id_raw, 10) : null;
```
`parseInt('__add_new_role__', 10)` evaluates to `NaN`. `JSON.stringify({role_id: NaN})` serializes `NaN` as `null` per the JSON spec. The API receives `role_id: null`, which the service interprets as "remove this person's role" (see CR-02 below). A person who had a role loses it silently — there is no error and no indication to the user.

**Fix:** Guard against NaN after `parseInt`, and prevent the main save form from submitting when the sentinel is active:

```ts
// In +page.server.ts, after line 103:
if (role_id_raw && isNaN(role_id)) {
  return fail(400, { error: 'Please complete role selection before saving.' });
}
```

Additionally, in the Svelte component the outer save `<button type="submit">` should be disabled while `showAddRoleForm` is true, or the sentinel value should be excluded from the `<select name="role_id">` element entirely (use a separate hidden field that is only populated when a real role is selected).

---

### CR-02: `update_person` unconditionally overwrites `role_id` — breaks PATCH semantics and can silently clear roles

**File:** `api/services/admin_people.py:222`

**Issue:** Line 222 is:
```python
person.role_id = body.role_id
```
This executes unconditionally. `PersonUpdate.role_id` defaults to `None` (line 84 of `admin_people.py`). Any PATCH request that omits `role_id` from the JSON body will have `body.role_id == None`, and the service will write `NULL` to `person.role_id`, silently removing the existing role.

The docstring says "role_id may be explicitly set to None (remove role) or a new id" — but the schema makes `None` the default value for an _absent_ field, so absent and explicit-null are indistinguishable at this layer. This creates a footgun for any future caller that issues a partial PATCH.

This also makes the bug in CR-01 a data-loss path rather than a validation failure: by the time the serialized `null` arrives at the service, there is no way to know whether the client intentionally cleared the role or accidentally sent `null` due to the sentinel/NaN issue.

**Fix:** Apply the same guard used for `full_name` (line 219):
```python
# Only update role_id when the field was explicitly provided in the request body.
# Use model_fields_set to distinguish absent from explicit-null.
if "role_id" in body.model_fields_set:
    person.role_id = body.role_id
```
Pydantic v2's `model_fields_set` contains only the field names that were present in the incoming JSON, making absent vs. explicit-null distinguishable. Apply the same pattern to `bio_text` and `photo_url` (lines 224-225) for consistency, since those fields also default to `None` and the same ambiguity exists.

---

## Warnings

### WR-01: `create_role` has a TOCTOU race that can raise an unhandled `IntegrityError`

**File:** `api/services/admin_people.py:262-270`

**Issue:** The find-or-create pattern does a `SELECT` then conditional `INSERT`:
```python
result = await db.execute(select(Role).where(Role.name == name))
role = result.scalar_one_or_none()
if role is not None:
    return {"id": role.id, "name": role.name}
role = Role(name=name)
db.add(role)
await db.flush()
await db.commit()
```
Two concurrent requests for the same role name can both pass the `if role is not None` guard and both reach `db.flush()`. The second flush will raise `sqlalchemy.exc.IntegrityError` (from the unique constraint on `roles.name`). This exception is not caught and propagates as an unhandled 500 to the caller. The router must catch `IntegrityError` or the service must use `INSERT ... ON CONFLICT DO NOTHING` to be safe.

**Fix:**
```python
from sqlalchemy.exc import IntegrityError

try:
    role = Role(name=name)
    db.add(role)
    await db.flush()
    await db.commit()
    await db.refresh(role)
    return {"id": role.id, "name": role.name}
except IntegrityError:
    await db.rollback()
    # Re-fetch the row that won the race
    result = await db.execute(select(Role).where(Role.name == name))
    role = result.scalar_one()
    return {"id": role.id, "name": role.name}
```

---

### WR-02: `full_name` derivation in `update_person` uses raw `body.*` values after normalizing `person.*` — middle/suffix inconsistency possible

**File:** `api/services/admin_people.py:239-245`

**Issue:** The service normalizes the name parts into `person.*` at lines 229-232 (empty string → None) before reaching the derivation block at line 239. The derivation then passes `body.middle_name` and `body.name_suffix` — the raw, un-normalized values — to `_derive_full_name`:

```python
person.first_name = body.first_name if body.first_name else None   # line 229
...
if body.first_name and body.last_name:
    person.full_name = _derive_full_name(
        body.first_name,
        body.middle_name,   # <-- raw body value, not person.middle_name
        body.last_name,
        body.name_suffix,   # <-- raw body value, not person.name_suffix
    )
```

`_derive_full_name` handles empty string middle/suffix correctly (the `" ".join(p for p in [...] if p)` filter discards empty strings), so this does not produce an incorrect derived name. However, the pattern is inconsistent: `person.middle_name` is already set to the normalized value at this point but the derivation bypasses it. If `_derive_full_name` were ever changed to not filter falsy parts, this would silently regress.

**Fix:** Use `person.middle_name` and `person.name_suffix` (the already-normalized values) as arguments to `_derive_full_name`:
```python
if body.first_name and body.last_name:
    person.full_name = _derive_full_name(
        body.first_name,
        person.middle_name,    # already normalized to None if blank
        body.last_name,
        person.name_suffix,    # already normalized to None if blank
    )
```

---

### WR-03: `appointing_president_party` is not `.trim()`-ed in the server action

**File:** `app/src/routes/admin/people/[id]/+page.server.ts:111`

**Issue:** Every other text field in the `save` action is `.trim()`-ed before being sent to the API. `appointing_president_party` is the exception:
```ts
const appointing_president_party = ((formData.get('appointing_president_party') as string) ?? '') || null;
```
Compare to every other field:
```ts
const appointing_president = ((formData.get('appointing_president') as string) ?? '').trim() || null;
```
While the party value comes from a `<select>` whose options have no whitespace, the pattern is inconsistent and would silently store a leading/trailing space if the field were ever changed to a free-text input. It also means if a browser or test sends a value with whitespace, no normalization occurs.

**Fix:**
```ts
const appointing_president_party = ((formData.get('appointing_president_party') as string) ?? '').trim() || null;
```

---

## Info

### IN-01: Phase 9 fields missing from `test_person_update_with_all_fields` test

**File:** `api/tests/test_admin_people_schemas_service.py:141-155`

**Issue:** `test_person_update_with_all_fields` (line 141) constructs a `PersonUpdate` with `full_name`, `role_id`, `bio_text`, `photo_url`, and `tenures`, but does not include any of the six Phase 9 fields (`first_name`, `last_name`, `middle_name`, `name_suffix`, `appointing_president`, `appointing_president_party`). There is no test confirming that Phase 9 fields are accepted by `PersonUpdate` or round-tripped through `PersonDetail`.

**Fix:** Add a test that instantiates `PersonUpdate` with all Phase 9 fields and verifies each is accessible; add a complementary test for `PersonDetail` that includes the Phase 9 fields. These are schema-level tests — no DB required.

---

### IN-02: `use:enhance` callback has dead `result.type === 'redirect'` branch

**File:** `app/src/routes/admin/people/[id]/+page.svelte:110-117`

**Issue:** The `use:enhance` return callback for the save form is:
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
Both branches call `await update()` with identical arguments. The `result.type === 'redirect'` branch is also unreachable in practice: SvelteKit's `use:enhance` intercepts `redirect` results and navigates automatically before invoking the callback, so the callback never receives a `'redirect'` result type. The conditional adds no logic and misleads future readers.

**Fix:** Collapse to a single `await update()` call:
```ts
return async ({ update }) => {
    saveSubmitting = false;
    await update();
};
```

---

_Reviewed: 2026-06-19T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
