---
phase: 18-people-schema-editor
reviewed: 2026-06-29T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - alembic/versions/0010_add_is_justice.py
  - api/models/models.py
  - api/schemas/admin_people.py
  - api/services/admin_people.py
  - api/tests/test_admin_people_schemas_service.py
  - app/src/routes/admin/people/+page.server.ts
  - app/src/routes/admin/people/+page.svelte
  - app/src/routes/admin/people/[id]/+page.server.ts
  - app/src/routes/admin/people/[id]/+page.svelte
  - tests/test_schema.py
findings:
  critical: 3
  warning: 4
  info: 3
  total: 10
status: issues_found
---

# Phase 18: Code Review Report

**Reviewed:** 2026-06-29
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Phase 18 adds the `is_justice` boolean column to the `people` table, surfaces it in the admin people directory (badge) and edit form (checkbox), conditionally renders Justice-only sections (Role, Court Tenure, Appointment), and extends the service/schema layers to read and write the field. The migration, ORM model, schemas, and service logic are structurally sound. Three blockers were found, all in the SvelteKit layer:

1. The `save` action unconditionally sends `is_justice: true/false` — toggling `is_justice` off while having entered no structured name parts silently clears `bio_text` and `photo_url` because the `photo` action is bypassed.
2. More critically: `role_id` is **always** overwritten from the PATCH body regardless of whether `body.role_id` is `None`, due to an unconditional assignment in `update_person`. Combined with the save action never sending a `role_id` for non-Justice persons, this reliably NULLs the role on every save for advocates.
3. The `delete_person_if_orphan` service deletes `SpeakerAlias` rows before checking whether the person is actually orphaned for the other three FK tables — if the person is not orphaned, the alias rows are silently gone and the function returns `False` without restoring them.

---

## Critical Issues

### CR-01: `update_person` unconditionally overwrites `role_id` — silently NULLs role on every non-Justice save

**File:** `api/services/admin_people.py:275`

**Issue:** The assignment `person.role_id = body.role_id` is unconditional. `PersonUpdate.role_id` defaults to `None`, and the `save` action in `+page.server.ts` only includes `role_id` in the PATCH body when a Justice's role select is visible (`{#if isJustice}`). For any person where `is_justice` is `False` (the majority of people — advocates, counsel), the save action sends `role_id: null` in every PATCH. The service immediately writes that `None` to the database, erasing whichever role the person had. The comment on line 274 says "role_id may be explicitly set to None (remove role)" — but this is indistinguishable from "not provided". Every advocate save is a silent role deletion.

**Fix:** Guard the assignment the same way other optional fields are guarded:
```python
# Only write role_id when the caller explicitly supplies one (None = leave unchanged)
if body.role_id is not None:
    person.role_id = body.role_id
```
Alternatively, use a sentinel (e.g. `omit` / `Unset`) rather than overloading `None` to mean both "clear" and "not provided". Given the existing `Optional[bool]` pattern used for `is_justice` (where `None` means leave unchanged), `role_id` should follow the same convention. The `save` action must then explicitly send the sentinel when the operator intends to clear the role.

---

### CR-02: `delete_person_if_orphan` destroys `SpeakerAlias` rows before confirming orphan status — no rollback path

**File:** `api/services/admin_people.py:424-439`

**Issue:** The function deletes all `SpeakerAlias` rows for the person at line 424-428, then loops over `Utterance`, `CaseAppearance`, and `ArgumentParticipant` to check counts. If any of those has `count > 0`, the function returns `False` (person is not orphaned) without committing. However, the alias DELETE has already been executed on the active session. Because the function relies on SQLAlchemy's implicit transaction, the alias deletes are sitting in the transaction — uncommitted — when `False` is returned. Whether those deletes are rolled back depends entirely on what the caller does next. Looking at the router (`admin.py:606-614`), on a `False` return it immediately raises `HTTPException(409)`, which exits the FastAPI request scope. FastAPI's `AsyncSession` dependency (via `get_db`) typically issues a rollback on exception, so the aliases are likely saved in practice. But this is fragile: the correctness of the orphan check depends on the caller's exception handling, not on the function's own logic. If the `get_db` dependency ever changes, or the function is called from a context that commits on `False`, aliases are silently destroyed.

**Fix:** Check counts first across all four FK tables, then only delete aliases as the final step immediately before deleting the person:
```python
async def delete_person_if_orphan(db: AsyncSession, person_id: int) -> bool | None:
    result = await db.execute(select(Person).where(Person.id == person_id))
    person = result.scalar_one_or_none()
    if person is None:
        return None

    # Check all FK tables BEFORE any destructive operation
    for model, col in [
        (Utterance, Utterance.person_id),
        (CaseAppearance, CaseAppearance.person_id),
        (ArgumentParticipant, ArgumentParticipant.person_id),
    ]:
        count = (await db.execute(
            select(sqlfunc.count()).select_from(model).where(col == person_id)
        )).scalar_one()
        if count > 0:
            return False  # Not orphaned — no destructive ops have run

    # Only now delete aliases (intrinsic to person) and then the person row
    await db.execute(
        delete(SpeakerAlias)
        .where(SpeakerAlias.person_id == person_id)
        .execution_options(synchronize_session=False)
    )
    await db.execute(
        delete(Person)
        .where(Person.id == person_id)
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    return True
```

---

### CR-03: `save` action sends `is_justice` as a boolean but does not include `bio_text` or `photo_url` — toggling is_justice off then saving clears no fields, but the UI state is misleading

**File:** `app/src/routes/admin/people/[id]/+page.server.ts:167`

**Issue:** The checkbox sends `'on'` when checked; the action coerces this to `is_justice = formData.get('is_justice') === 'on'`, so unchecking sends `is_justice: false`. This is correct boolean coercion. However, the bug is subtler: `is_justice` is always sent as a concrete boolean (never `null`) from the save action. The `PersonUpdate` schema documents `None` as meaning "leave unchanged", but `false` is a valid operational value meaning "this person is not a Justice". This is intentional for the checkbox case. The actual blocker here is a UX data loss path:

When a user unchecks "Is Justice" and clicks "Save changes", the Court Tenure and Appointment sections disappear from the DOM (they are inside `{#if isJustice}` blocks). The tenure rows in the hidden `<input name="tenures">` are serialized from the current `$state` — but the hidden tenure input is also inside `{#if isJustice}` (line 489). When `isJustice` is `false` the entire Court Tenure card including the hidden input is not rendered, so no `tenures` field is submitted. `PersonUpdate.tenures` defaults to `None` (leave unchanged). So tenures are correctly preserved. However: the `role_id` field is also inside `{#if isJustice}` (lines 301-398), meaning no `role_id` is submitted, which triggers CR-01's unconditional overwrite and NULLs the role. This confirms CR-01 is a real data loss path triggered by the is_justice toggle.

**Fix:** This CR is contingent on CR-01 — fixing the unconditional `role_id` assignment resolves the data loss. Mark this as a documentation/cross-ref finding: CR-01 fix is mandatory; this finding establishes the triggering path.

---

## Warnings

### WR-01: `test_schema.py` comment says "10 tables" but `EXPECTED_TABLES` has 11 entries — test docstring says "11 tables" — mismatch in module docstring

**File:** `tests/test_schema.py:51`

**Issue:** The module-level docstring on line 3 says "All 11 expected tables exist" but the section comment immediately above `EXPECTED_TABLES` on line 51 says "Test 1: All 10 tables exist post-migration". The `EXPECTED_TABLES` set has 11 entries (correct). The discrepancy is documentation-only but `admin_jobs` is also missing from `EXPECTED_TABLES` — the models file defines 12 tables (roles, people, court_tenures, cases, arguments, case_arguments, case_appearances, argument_participants, pipeline_runs, utterances, speaker_alias, **admin_jobs**). The test will pass even though `admin_jobs` is not asserted. A future migration that accidentally drops `admin_jobs` would not be caught.

**Fix:** Add `admin_jobs` to `EXPECTED_TABLES` and correct the section comment to "All 12 tables":
```python
EXPECTED_TABLES = {
    "roles",
    "people",
    "court_tenures",
    "cases",
    "arguments",
    "case_arguments",
    "case_appearances",
    "argument_participants",
    "pipeline_runs",
    "utterances",
    "speaker_alias",
    "admin_jobs",  # missing from current set
}
```

---

### WR-02: `fetchMergePreview` in `+page.svelte` calls a same-origin SvelteKit route rather than going through the form action — bypasses the `use:enhance` pattern and uses client-side `fetch`, which means errors are silently swallowed on network failure

**File:** `app/src/routes/admin/people/[id]/+page.svelte:143-155`

**Issue:** `fetchMergePreview` calls `fetch('/admin/people/${data.person.id}/merge-preview?target_id=${targetId}')` in the client script. This is a browser-side `fetch` call to the SvelteKit API route. If the route returns a non-ok status, the code sets `mergeError = 'Could not load counts. Try again.'` — reasonable. But the `catch` branch (line 151-153) also sets the same `mergeError`. The actual concern: the merge preview count displayed before a destructive merge is fetched via an unauthenticated browser path. The SvelteKit `merge-preview/+server.ts` proxy does inject the `ADMIN_TOKEN` server-side before forwarding to FastAPI, so the token is not exposed. However, there is no CSRF protection or origin check on this GET endpoint. Any page loaded on the same browser session can call `/admin/people/{id}/merge-preview` and receive FK counts for any person. This is a minor information disclosure — counts are not sensitive — but it is worth noting since the admin token is correctly protected.

**Fix:** No immediate code change required if the route is admin-authenticated at the router level. Confirm that the SvelteKit admin routes are protected by a session/cookie check upstream (not just relying on the hidden `ADMIN_TOKEN`). If session auth is absent, add a same-origin check or session cookie to the merge-preview GET handler.

---

### WR-03: `PersonListItem` client-side type in `[id]/+page.server.ts` does not include `is_justice`, `missing`, or `role_name` fields that the API actually returns

**File:** `app/src/routes/admin/people/[id]/+page.server.ts:37-45`

**Issue:** The `PersonListItem` interface defined at line 37 for the merge picker and role dropdown includes only `id`, `full_name`, `last_name`, `first_name`, `role_id`, `role_name`. The FastAPI response also includes `missing: string[]` and `is_justice: boolean`. The TypeScript type is narrower than the actual payload. This is not currently a bug because the only consumer uses `p.role_id`, `p.role_name`, `p.id`, `p.last_name`, `p.first_name` — all of which are in the interface. But if a future developer references `item.is_justice` from this typed list, TypeScript will reject it and they will be forced to cast, potentially masking a real type mismatch.

**Fix:** Expand the interface to match the full `PersonListItem` response:
```typescript
interface PersonListItem {
    id: number;
    full_name: string;
    last_name: string | null;
    first_name: string | null;
    role_id: number | null;
    role_name: string | null;
    missing: string[];
    is_justice: boolean;
}
```

---

### WR-04: `_replace_tenures` uses `t.seat or None` after already checking `t.seat or t.start_date` — inconsistent handling of seat='' (empty string)

**File:** `api/services/admin_people.py:101, 113`

**Issue:** The filter on line 101 skips rows where both `t.seat` and `t.start_date` are falsy. Rows that pass this guard can have an empty-string `t.seat` (`t.seat = ''`) combined with a valid `t.start_date`. Line 113 then writes `seat=t.seat or None`, converting that empty string to `None` — correct normalization. But the initial guard uses `t.seat` (falsy check) while the insert uses `t.seat or None`. A row with `seat=''` and `start_date='2005-01-01'` would pass the filter and be inserted with `seat=None`. This is arguably correct behavior (empty seat becomes NULL) but the intent is not documented and the filter condition is subtly different from the insert normalization. If the operator leaves the seat field blank but fills in a date, the tenure is saved with a NULL seat silently, which may be intentional per D-09 but is not guarded against by the schema (CourtTenure.seat is `nullable=True`).

**Fix:** Either document this is intentional, or normalize the seat to `None` before the filter and use the normalized value for both the guard and the insert:
```python
for t in tenures:
    seat = t.seat.strip() if t.seat else None
    if not (seat or t.start_date):
        continue
    ...
    db.add(CourtTenure(person_id=person_id, seat=seat, ...))
```

---

## Info

### IN-01: `test_admin_people_schemas_service.py` Phase 18 tests do not verify `is_justice` appears in `PersonListItem.missing` derivation

**File:** `api/tests/test_admin_people_schemas_service.py:299-323`

**Issue:** The new Phase 18 tests verify that `is_justice` can be set on `PersonUpdate`, `PersonDetail`, and `PersonListItem`. They do not test that `is_justice=False` is the correct default returned by `list_people` when the DB column is `False`, nor that a person with `is_justice=True` gets the badge in the listing. These are integration-level concerns, but a unit test of `_missing_fields` with a `_FakePerson` that has `is_justice` attribute would confirm the derivation function still works correctly after the new field was added (it does not use `is_justice`, which is correct per D-04/D-06, but a test makes that explicit).

**Fix:** Consider adding a test asserting `_missing_fields` does not include `is_justice` in the missing list regardless of its value:
```python
def test_missing_fields_ignores_is_justice() -> None:
    from api.services.admin_people import _missing_fields
    person = _FakePerson(role_id=None, bio_text=None, photo_url=None)
    person.is_justice = True  # Should not appear in missing list
    assert "is_justice" not in _missing_fields(person)
```

---

### IN-02: `+page.svelte` merge preview calls `targetPerson?.full_name ?? targetPerson?.last_name ?? 'selected person'` but `PersonListItem` does not have `full_name` at the type level

**File:** `app/src/routes/admin/people/[id]/+page.svelte:733`

**Issue:** The `data.people` array is typed as `PersonListItem[]` (from `+page.server.ts`). The `PersonListItem` interface includes `full_name: string` (line 40 of `+page.server.ts`). The reference on line 733 is therefore type-safe. However, the fallback chain `targetPerson?.full_name ?? targetPerson?.last_name ?? 'selected person'` is ordering `full_name` before `last_name`, which is correct. The info note here is that `last_name` alone is an odd fallback display (shows only the last name, no first) — the option label already formats it as "last_name, first_name" for the picker, but the confirmation text would show only the last name. Low impact for an admin-only UI.

**Fix:** Cosmetic — consider `targetPerson?.full_name ?? [targetPerson?.last_name, targetPerson?.first_name].filter(Boolean).join(', ') ?? 'selected person'` to be consistent with the option label.

---

### IN-03: `+page.server.ts` `[id]` load function makes 3 serial HTTP calls — person detail, people list, merge-preview — increasing page load latency

**File:** `app/src/routes/admin/people/[id]/+page.server.ts:60-133`

**Issue:** The three `fetch` calls are sequential: person detail first (throws on 404/502), then people list, then merge-preview. The people list and merge-preview calls are independent of each other and could be parallelized with `Promise.all`. This is a quality note (performance is out of scope for v1 per the review brief) but the sequential pattern may cause noticeable latency on slow connections.

**Fix:** Out of v1 scope — flagged for awareness. Use `Promise.allSettled([peopleRes, previewRes])` if this becomes a user-facing concern.

---

_Reviewed: 2026-06-29_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
