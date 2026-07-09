---
phase: 27-people-admin
reviewed: 2026-07-09T00:00:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - alembic/versions/0016_add_person_birthdate.py
  - api/models/models.py
  - api/routers/admin.py
  - api/schemas/admin_people.py
  - api/services/admin_people.py
  - api/tests/test_admin_people_schemas_service.py
  - app/src/routes/admin/people/+page.server.ts
  - app/src/routes/admin/people/+page.svelte
  - app/src/routes/admin/people/[id]/+page.server.ts
  - app/src/routes/admin/people/[id]/+page.svelte
  - app/src/routes/admin/people/new/+page.server.ts
  - app/src/routes/admin/people/new/+page.svelte
findings:
  critical: 2
  warning: 4
  info: 4
  total: 10
status: issues_found
---

# Phase 27: Code Review Report

**Reviewed:** 2026-07-09
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

This supersedes the prior partial review of this file, which covered plans 27-01..27-06 and left the phase in a `fixed` state for four findings (the `update_person` partial-PATCH field-wipe bug, a NULL-`argued_date` tenure-gap false positive, discarded Birth Date/Tenure input on the create form, and stale test kwargs). Direct inspection of the current code confirms all four of those fixes are present and correct: `update_person` now branches on `body.model_fields_set` for every optional field (`api/services/admin_people.py:410-434`), the tenure-gap query explicitly excludes `NULL` `argued_date` rows (`api/services/admin_people.py:252-257`), the create-person page no longer renders Birth Date/Tenure Period inputs, and the removed-schema-field test kwargs are gone. Two findings from that pass were explicitly left unfixed (dead `first_name`/`last_name` fields in the merge picker, and a docstring overstatement) and are carried forward below.

This pass is a full review of all 9 plans, including the two later gap-closure plans (27-08: `PersonCreateRequest` name-part fields; 27-09/UAT: the curated President's Party dropdown and the "Person Type" card restructuring). That restructuring introduces **two new, more severe data-loss bugs** than anything in the prior pass: the hidden `tenures`/`birthdate` inputs on `[id]/+page.svelte` are nested inside the `{#if isJustice}` block, so toggling a Justice to "Advocate" and saving silently deletes their entire tenure history and birthdate — directly contradicting the service's own documented intent to preserve tenure rows in that case (D-06/D-07). Separately, the component's own SvelteKit soft-navigation reset effect resets `isJustice`/`birthdate`/merge state on a person-id change but forgets `tenureRows`, so navigating to a different person (e.g., immediately after a merge redirect) and saving can silently overwrite that person's real tenure data with a stale array from whoever was viewed previously. Both are BLOCKER — this is exactly the kind of "pipeline runs are disposable, but a person's biographical record is not" data-permanence violation this project treats as a hard constraint.

## Critical Issues

### CR-01: Toggling a Justice to "Advocate" and saving silently deletes all tenure history and birthdate

**File:** `app/src/routes/admin/people/[id]/+page.svelte:477-655`
**Issue:**
The hidden `<input type="hidden" name="tenures" ... />` (line 653) and the visible `Birth Date` input (lines 488-495) are both nested inside `{#if isJustice} ... {/if}` (opens line 477, closes line 655). The Bench/Advocate segmented toggle (lines 434-470) has no confirmation step — clicking "Advocate" on an existing Justice's edit page immediately flips local `isJustice` state and un-renders this entire block, including those two inputs, from the DOM.

In `app/src/routes/admin/people/[id]/+page.server.ts`'s `save` action:
```ts
const birthdate = ((formData.get('birthdate') as string) ?? '').trim() || null;
const tenuresRaw = (formData.get('tenures') as string) ?? '[]';
```
Because the inputs are absent from `FormData` whenever `isJustice === false` at submit time, `birthdate` resolves to `null` and `tenuresRaw` resolves to `'[]'` — unconditionally, regardless of what data previously existed. This is sent as an explicit `PATCH` body (`{ ..., birthdate: null, tenures: [] }`).

`api/services/admin_people.py`'s `update_person` explicitly documents that switching `is_justice` to `False` should **not** delete tenure rows:
```python
# Phase 18: write is_justice only when body supplies a non-None value (D-08)
# ...
# Does NOT delete tenure rows when is_justice is False (D-06, D-07).
if body.is_justice is not None:
    person.is_justice = body.is_justice

if body.tenures is not None:
    # May raise ValueError on malformed date — caller catches and returns 422
    await _replace_tenures(db, person_id, body.tenures)
```
But because `body.tenures` arrives as `[]` (not `None`), this guard does not help — `_replace_tenures(db, person_id, [])` still deletes every existing `CourtTenure` row for that person (seat, start/end dates, appointing president and party) and inserts nothing. `birthdate` is wiped the same way (it is present in `fields_set` because the frontend JSON body always includes the key, with value `null`).

Net effect: any operator who toggles an existing Justice's Person Type card to "Advocate" — even briefly, even by misclick, with zero confirmation UI — and then clicks "Save Person" permanently destroys that Justice's entire tenure history and birthdate. There is no undo.

**Fix:** Move both the tenures hidden input and the Birth Date input outside the `{#if isJustice}` block so they are always part of `save-form` regardless of the toggle's current value, e.g.:
```svelte
<!-- Always present, independent of the Bench/Advocate toggle, so `save`
     always receives the true current tenure/birthdate state. -->
<input type="hidden" name="birthdate" form="save-form" value={birthdate} />
<input type="hidden" name="tenures" form="save-form" value={JSON.stringify(tenureRows)} />

{#if isJustice}
  <!-- visible Birth Date <input> and tenure-row UI stay here, bound to the
       same state variables the always-present hidden inputs above read from -->
{/if}
```
As defense in depth, also consider having the backend refuse to clear tenures via an implicit `is_justice=False` transition unless the caller passes an explicit "confirm tenure deletion" flag.

### CR-02: Stale tenure rows from a previously-viewed person can overwrite a different person's tenures (e.g., right after a merge)

**File:** `app/src/routes/admin/people/[id]/+page.svelte:56-73, 125-133`
**Issue:**
`tenureRows` (and the `nextKey` counter) are initialized once from `data.person.tenures` at component creation:
```ts
let tenureRows = $state<TenureRow[]>(
	(data.person.tenures ?? []).map((t) => ({ _key: nextKey++, ... }))
);
```
The component's own comment correctly identifies that SvelteKit reuses this component instance across soft navigations to a *different* `person.id`, and adds a reset effect for exactly that reason:
```ts
// Reset merge/type state when navigating to a different person (SvelteKit soft
// navigation reuses the component — $state variables must be reset manually
// when person.id changes).
$effect(() => {
	data.person.id;
	mergeTargetId = '';
	mergePreview = null;
	mergeError = null;
	mergeLoading = false;
	isJustice = data.person.is_justice ?? false;
	birthdate = data.person.birthdate ?? '';
});
```
`tenureRows`/`nextKey` are conspicuously missing from this list. The `merge` action (`+page.server.ts:274-305`) redirects on success to `/admin/people/{target_id}` — a different person id on the same route, exactly the soft-navigation case the comment warns about. After a merge, `data.person` updates to the target person (name, identity, birthdate all correctly reset by the effect above), but `tenureRows` still holds the **source** person's stale tenure array.

If the operator then clicks "Save Person" on this post-merge page (a very plausible next step — e.g., to also fix a typo in the target's name), the stale `tenures` hidden-input value is submitted, and `update_person` will `_replace_tenures` the target's real, correct tenure rows with the wrong, stale ones from the just-merged-away source person.

**Fix:** Include `tenureRows`/`nextKey` in the same reset effect:
```ts
$effect(() => {
	data.person.id;
	mergeTargetId = '';
	mergePreview = null;
	mergeError = null;
	mergeLoading = false;
	isJustice = data.person.is_justice ?? false;
	birthdate = data.person.birthdate ?? '';
	nextKey = 1;
	tenureRows = (data.person.tenures ?? []).map((t) => ({
		_key: nextKey++,
		seat: t.seat ?? '',
		start_date: t.start_date ?? '',
		end_date: t.end_date ?? '',
		appointed_by: t.appointed_by ?? '',
		appointing_president_party: t.appointing_president_party ?? '',
	}));
});
```

## Warnings

### WR-01: Merge-target picker never renders "Last, First" — dead TS fields, carried forward from the prior review (unfixed)

**File:** `app/src/routes/admin/people/[id]/+page.server.ts:39-44`, `app/src/routes/admin/people/[id]/+page.svelte:702-707`
**Issue:** The local `PersonListItem` TypeScript interface declares `last_name`/`first_name`, and the merge-target `<select>` reads them to format options as `"Lastname, Firstname"`:
```svelte
{p.last_name ? `${p.last_name}, ${p.first_name ?? ''}` : p.full_name}
```
The server's `PersonListItem` Pydantic response model (`api/schemas/admin_people.py:47-71`) has no `first_name`/`last_name` fields, so `GET /api/admin/people` never returns them — `p.last_name` is always `undefined`, and the ternary always falls through to `p.full_name`. The prior review flagged this and it was explicitly left unfixed ("predates Phase 27, unrelated to it"); it remains present in the final, complete Phase 27 code and is worth a second look now that the phase is fully closing out, since the merge picker is squarely a Phase 27/Phase 12 admin-people surface.
**Fix:** Either add `first_name`/`last_name` to the server `PersonListItem` schema and `list_people`'s output, or drop the dead `last_name`/`first_name` branch and the two unused interface fields from the client.

### WR-02: Photo-by-URL fetch has no host allowlist, unlike the sibling PDF-URL validator

**File:** `api/routers/admin.py:741-752`
**Issue:** `_validate_pdf_url` (lines 171-191) restricts ingest URLs to `https://…supremecourt.gov` specifically to mitigate SSRF (T-07-01). The photo-by-URL path in `upload_person_photo` only checks the scheme:
```python
_parsed_url = _urlparse(photo_url)
if _parsed_url.scheme != 'https':
    raise HTTPException(status_code=422, detail="Photo URL must use HTTPS.")
...
r = await client.get(photo_url, follow_redirects=False)
```
Any admin-authenticated request can direct the server to issue an HTTPS GET to an arbitrary host (internal services, cloud metadata endpoints reachable over HTTPS, etc.) before the Pillow validation ever runs — the request itself, and any resulting error detail, already completes regardless of whether the response turns out to be an image.
**Fix:** Apply the same allowlist discipline used for `_validate_pdf_url`, or at minimum reject requests that resolve to private/link-local/loopback address ranges before issuing the `httpx` GET.

### WR-03: Overly broad exception handling in image validation masks unrelated failures

**File:** `api/routers/admin.py:728-736, 754-759`
**Issue:** Both image-validation blocks use `except (UnidentifiedImageError, Exception):`. Since `Exception` is already a superset of `UnidentifiedImageError`, the more specific exception is redundant, and the broad catch-all also swallows unrelated bugs (a stray `TypeError`, an `OSError` mid-read, etc.), surfacing them to the operator as the generic "not a valid image" message and discarding the real cause.
**Fix:** Narrow to the exceptions Pillow actually documents for `Image.open`/`.verify()` (`UnidentifiedImageError`, `OSError`), and log the original exception server-side before returning the generic 422.

### WR-04: Gap-closure DB tests are effectively unreachable in CI, leaving Plan 27-08's fix unverified by automation

**File:** `api/tests/test_admin_people_schemas_service.py:380-383`
**Issue:** The skip guard for the two new `create_person` name-part tests is:
```python
def _db_configured() -> bool:
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"
```
The `"sk-ant" not in url` check (an Anthropic API-key prefix substring) has no relationship to a Postgres/asyncpg connection string and reads as a copy/paste artifact. More importantly, unless the test/CI environment explicitly sets a real `DATABASE_URL`, both `test_create_person_persists_name_parts_when_supplied` and `test_create_person_leaves_name_parts_none_when_omitted` — the tests specifically added to close UAT Gap 3 — are skipped, so the behavior they exist to verify has no default automated coverage.
**Fix:** Remove the unrelated `"sk-ant"` check; confirm the CI configuration actually sets `DATABASE_URL` so these two tests run, or move the pure "name parts persist/omit" assertions into a lighter test that doesn't require a live database.

## Info

### IN-01: Orphaned Role schema/service/route left in place across three files

**File:** `api/schemas/admin_people.py:164-182`, `api/services/admin_people.py:499-519`, `api/routers/admin.py:1018-1033`
**Issue:** `RoleCreate`, `RoleResponse`, `create_role`, and `POST /api/admin/roles` are each marked `TODO(D-10): orphaned by Phase 27 — person-level roles removed; safe to delete once confirmed.` The plan that removed the only caller (the `createRole` form action) has landed, so this is now confirmed-dead code.
**Fix:** Delete `RoleCreate`/`RoleResponse` from the schema, `create_role` from the service, and the `POST /roles` route from the router in a follow-up cleanup pass.

### IN-02: `list_participants_for_job` still joins the now-superseded person-level Role

**File:** `api/services/admin_people.py:716-730`
**Issue:** This function still does `.outerjoin(Role, Person.role_id == Role.id)` and returns `role_name` on `ParticipantItem`. Per Phase 27 (D-10), person-level Role is superseded — `PersonCreateRequest`/`PersonUpdate` no longer expose `role_id` for writing, so for any person created or edited after Phase 27, `Person.role_id` can never be populated and `role_name` will always resolve to `None` for such people. Harmless today, but a future reader could mistake this for a still-live write path.
**Fix:** Add a short comment noting this is legacy-data-only, or remove the join once confirmed no legacy `role_id` data remains meaningful.

### IN-03: No schema-level (non-DB) unit test for `birthdate` or `PersonCreateRequest`'s name-part fields

**File:** `api/tests/test_admin_people_schemas_service.py`
**Issue:** The file thoroughly unit-tests `_missing_fields`, `_derive_full_name`, and several schema shapes, but there is no pure test asserting `PersonUpdate.birthdate` defaults to `None`/accepts an ISO string, or that `PersonCreateRequest` accepts/omits the four Phase 27 Plan 08 name-part fields at the schema layer — the only coverage for the latter is the two DB-guarded tests flagged in WR-04, which are typically skipped.
**Fix:** Add lightweight schema-only tests, e.g. `PersonUpdate(birthdate="1955-01-27").birthdate == "1955-01-27"` and `PersonCreateRequest(full_name="X", is_justice=True).first_name is None`.

### IN-04: `_replace_tenures`/`update_person` docstrings overstate the "no write happens before validation" guarantee (carried forward, unfixed)

**File:** `api/services/admin_people.py:131-134, 429-431`
**Issue:** Both docstrings claim a malformed tenure date "raises ValueError... before any DB write completes." In practice, by the time `_replace_tenures` runs, every other field has already been mutated on the ORM-tracked `person` object, and `_replace_tenures` itself has already issued the `DELETE FROM court_tenures` statement before parsing/inserting new rows. Whether that `DELETE` is actually rolled back depends entirely on the `get_db` session dependency's exception-exit behavior, not on anything in this function.
**Fix:** Tighten the wording to "no commit occurs," or reorder `_replace_tenures` ahead of the other field mutations so the ordering matches the documented intent.

---

_Reviewed: 2026-07-09_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
