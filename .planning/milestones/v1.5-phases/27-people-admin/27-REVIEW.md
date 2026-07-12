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
  critical: 1
  warning: 8
  info: 6
  total: 15
status: issues_found
---

# Phase 27: Code Review Report

**Reviewed:** 2026-07-09
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Reviewed the full People Admin surface (migration, models, router, schemas, service, tests, and all four SvelteKit route files) at the current HEAD, which includes Plan 27-10's CR-01/CR-02 data-loss fixes and Plan 27-11's follow-up fix for the `effect_update_depth_exceeded` regression that 27-10 introduced.

**27-11 regression check (verified, no regression):** `app/src/routes/admin/people/[id]/+page.svelte`'s person-id-change reset `$effect` (lines 125-151) now derives tenure `_key` values from a local, non-`$state` `resetKey` counter (line 133) and only *writes* the `$state` `nextKey` once at the end (line 150: `nextKey = resetKey;`), instead of reading-and-incrementing `nextKey` itself inside the effect. Because the effect body no longer *reads* `nextKey`, it no longer creates the self-dependency that caused the infinite-update loop — this is a correct, minimal fix. I separately re-verified that the CR-01 hidden `birthdate`/`tenures` inputs (lines 499-500, `form="save-form"`) remain outside the `{#if isJustice}` block, and that the CR-02 `model_fields_set` guard in `update_person` (`api/services/admin_people.py:410-434`) is untouched by 27-11 — both fixes remain intact.

While tracing the same file for other reactive-state hazards (per this review's scope), I found a narrow race condition between the merge-preview fetch and the person-change reset effect (WR-08). Separately, standard-depth review of the rest of the file set surfaced one Critical finding — `CourtTenure` rows are omitted from the merge/delete FK bookkeeping in `api/services/admin_people.py`, which will crash (rather than gracefully block) any attempt to merge or delete a Bench person who has tenure rows, a very plausible action given this phase adds full tenure-row CRUD to the People editor — plus a set of Warning/Info issues spanning dead client fields, an SSRF gap, an unguarded silent full-name overwrite, test-config gaps, and some dead/legacy code.

## Critical Issues

### CR-01: Merging or deleting a person with `CourtTenure` rows crashes with an unhandled `IntegrityError`

**File:** `api/services/admin_people.py:522-545` (`get_merge_preview`), `api/services/admin_people.py:548-594` (`merge_people`), `api/services/admin_people.py:597-636` (`delete_person_if_orphan`)

**Issue:** `CourtTenure.person_id` is `nullable=False` with a plain `ForeignKeyConstraint(["person_id"], ["people.id"])` and no `ON DELETE CASCADE` anywhere in any Alembic migration (confirmed — no `ondelete=` clause exists in `alembic/versions/`). None of the three merge/delete code paths account for `CourtTenure`:

- `get_merge_preview`'s counted-tables loop (lines 535-540) only counts `utterances`, `aliases` (`SpeakerAlias`), `appearances` (`CaseAppearance`), and `argument_participants`. It never counts `CourtTenure`, so the operator-facing merge preview (rendered in `[id]/+page.svelte:733-756`) understates what a merge actually affects.
- `merge_people`'s transfer loop (lines 574-586) re-points `Utterance`, `SpeakerAlias`, `CaseAppearance`, and `ArgumentParticipant` rows to the target but never touches `CourtTenure`. The subsequent `delete(Person).where(Person.id == source_id)` (lines 587-591) then violates the FK constraint from any remaining `CourtTenure` row and raises an unhandled `IntegrityError` — there is no `try/except` around it, so it surfaces to the operator as a raw 500 instead of the documented 422 (`T-12-SELF`) contract.
- `delete_person_if_orphan`'s orphan check (lines 619-628) only inspects `Utterance`/`CaseAppearance`/`ArgumentParticipant`. A Bench person with zero rows in those three tables but with one or more `CourtTenure` rows (a normal state for a Justice given tenure data via the People editor but not yet linked to any argument) passes the orphan check, is reported `can_delete=true` to the client (`[id]/+page.server.ts:95-112`), and then the final `delete(Person)` (lines 630-634) raises the same unhandled `IntegrityError`.

Because this phase specifically adds Bench tenure-period CRUD to the People editor, this is not an obscure edge case: any Justice with tenure data will hit this path the first time an operator tries to merge or delete them.

**Fix:**
```python
# get_merge_preview: count CourtTenure too
for key, model, col in [
    ("utterances", Utterance, Utterance.person_id),
    ("aliases", SpeakerAlias, SpeakerAlias.person_id),
    ("appearances", CaseAppearance, CaseAppearance.person_id),
    ("argument_participants", ArgumentParticipant, ArgumentParticipant.person_id),
    ("tenures", CourtTenure, CourtTenure.person_id),  # add
]:
    ...

# merge_people: transfer CourtTenure rows too
for model, col in [
    (Utterance, Utterance.person_id),
    (SpeakerAlias, SpeakerAlias.person_id),
    (CaseAppearance, CaseAppearance.person_id),
    (ArgumentParticipant, ArgumentParticipant.person_id),
    (CourtTenure, CourtTenure.person_id),  # add
]:
    await db.execute(
        update(model).where(col == source_id).values({col.key: target_id})
        .execution_options(synchronize_session=False)
    )

# delete_person_if_orphan: delete CourtTenure rows up front, the same way
# SpeakerAlias rows are treated as intrinsic-to-the-person (or, if tenure
# rows should instead BLOCK deletion, add CourtTenure to the orphan count
# loop — pick one and make it explicit):
await db.execute(
    delete(CourtTenure).where(CourtTenure.person_id == person_id)
    .execution_options(synchronize_session=False)
)
```
Update the `MergePreview` schema/response and the merge-preview UI copy if `tenures` becomes a new counted field.

## Warnings

### WR-01: Merge-target `<select>` never renders "Last, First" — dead client-side fields

**File:** `app/src/routes/admin/people/[id]/+page.server.ts:39-44`, `app/src/routes/admin/people/[id]/+page.svelte:722-725`

**Issue:** The local `PersonListItem` TypeScript interface declares `last_name`/`first_name`, and the merge-target dropdown reads them:
```svelte
{p.last_name ? `${p.last_name}, ${p.first_name ?? ''}` : p.full_name}
```
The server's `PersonListItem` Pydantic schema (`api/schemas/admin_people.py:47-71`) has no `first_name`/`last_name` fields, so `GET /api/admin/people` never returns them — `p.last_name` is always `undefined` and this always falls through to `p.full_name`.

**Fix:** Either add `first_name`/`last_name` to the server `PersonListItem` schema and `list_people` output, or drop the dead branch and the two unused interface fields client-side.

### WR-02: Photo-by-URL fetch has no host allowlist, unlike the sibling PDF-URL validator

**File:** `api/routers/admin.py:741-763`

**Issue:** `_validate_pdf_url` restricts ingest URLs to `https://…supremecourt.gov` specifically to mitigate SSRF (T-07-01). The photo-by-URL branch of `upload_person_photo` only checks the scheme:
```python
if _parsed_url.scheme != 'https':
    raise HTTPException(status_code=422, detail="Photo URL must use HTTPS.")
...
r = await client.get(photo_url, follow_redirects=False)
```
Any admin-authenticated request can direct the server to issue an HTTPS GET to an arbitrary host — internal services, cloud metadata endpoints reachable over HTTPS, etc. — before the Pillow validation ever runs. `follow_redirects=False` and the HTTPS requirement raise the bar but do not close the hole (a valid cert for a hostname that resolves, including via DNS rebinding, to an internal address still gets a request issued to it).

**Fix:** Apply the same allowlist discipline used for `_validate_pdf_url`, and/or resolve the hostname and reject private/link-local/loopback address ranges before issuing the request.

### WR-03: Overly broad exception handling in image validation masks unrelated failures

**File:** `api/routers/admin.py:732, 758`

**Issue:** Both image-validation blocks use `except (UnidentifiedImageError, Exception):`. `Exception` already subsumes `UnidentifiedImageError`, so the more specific exception is dead-weight, and the catch-all also swallows unrelated bugs (a stray `TypeError`, an `OSError` mid-read, an out-of-memory condition on a large upload) and reports them to the operator as a generic "not a valid image" 422 while discarding the real cause server-side.

**Fix:** Narrow to the exceptions Pillow documents for `Image.open`/`.verify()` (`UnidentifiedImageError`, `OSError`), and log the original exception before returning the generic 422.

### WR-04: DB-dependent tests don't honor the project's mandatory `statement_cache_size=0` asyncpg setting, and gate on an unrelated check

**File:** `api/tests/test_admin_people_schemas_service.py:380-383, 401-402, 452-453`

**Issue:** `CLAUDE.md` mandates: "asyncpg requires `statement_cache_size=0` when behind Digital Ocean PgBouncer (Transaction mode). This must be in the initial engine config." Both DB-guarded tests create their own engine directly:
```python
engine = create_async_engine(os.environ["DATABASE_URL"], echo=False)
```
with no `connect_args={"statement_cache_size": 0}`. If `DATABASE_URL` in the test environment ever points at a PgBouncer-fronted (transaction-mode) instance, these two tests are liable to fail with asyncpg prepared-statement errors — exactly the class of failure this project's memory log already tracks as an open, pre-existing "FastAPI test lifespan/session-factory failure." Separately, the gating helper:
```python
def _db_configured() -> bool:
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"
```
checks for the substring `"sk-ant"` (an Anthropic API-key prefix), which has no relationship to a Postgres connection string and reads as a copy/paste artifact from an unrelated guard.

**Fix:**
```python
engine = create_async_engine(
    os.environ["DATABASE_URL"], echo=False,
    connect_args={"statement_cache_size": 0},
)
```
Remove the unrelated `"sk-ant"` check, and confirm CI actually sets a real `DATABASE_URL` so these two tests run rather than silently skip.

### WR-05: `delete_person_if_orphan` deletes `SpeakerAlias` rows before the orphan check completes, relying entirely on implicit session-rollback-on-close

**File:** `api/services/admin_people.py:597-636`

**Issue:** The function unconditionally issues `DELETE FROM speaker_alias WHERE person_id = :id` (lines 612-617) *before* checking whether the person has zero rows in `Utterance`/`CaseAppearance`/`ArgumentParticipant`. If any of those three counts is nonzero, the function returns `False` at line 628 without ever calling `db.commit()` and without an explicit `db.rollback()`. Correctness depends entirely on the `get_db` session dependency discarding uncommitted work on request teardown — nothing in this function's own structure prevents a partial, silent alias deletion if a future refactor changes that session-lifecycle assumption (e.g., an intermediate commit gets added elsewhere in the same request, or a caller reuses the session).

**Fix:** Move the count checks (lines 619-628) before the `SpeakerAlias` delete, or wrap the whole sequence in an explicit transaction with a `try/except` that rolls back before returning `False`.

### WR-06: `update_person`'s full-name auto-derivation silently overwrites a manually-typed "Full name" value

**File:** `api/services/admin_people.py:439-445`, `app/src/routes/admin/people/[id]/+page.server.ts:137-183`

**Issue:**
```python
if body.first_name and body.last_name:
    person.full_name = _derive_full_name(
        body.first_name, body.middle_name, body.last_name, body.name_suffix,
    )
```
The `[id]` editor's `save` action always sends `first_name`/`last_name` (trimmed, or `null`) alongside `full_name` in every submission — they are not split across separate forms the way `bio_text`/`photo_url` are (lines 137-183 of `+page.server.ts`). Consequently, for any person who already has both `first_name` and `last_name` populated (the common case for anyone past initial data entry), **every** "Save Person" click recomputes `full_name` from the structured parts and silently overwrites whatever string the operator typed directly into the "Full name" input — even a deliberate deviation from the mechanical `first + middle + last + suffix` concatenation (a nickname, stage name, historical spelling). The UI presents "Full name" as a freely editable text field with no indication it is derived/overridden whenever the name-part fields are populated.

**Fix:** Either make "Full name" genuinely authoritative (drop the auto-derivation, or only derive it when the operator hasn't also changed `full_name` directly in the same submission), or make the UI honestly reflect the derived nature of the field (disable it, or add a note that it is computed from the parts below) so this stops being a silent overwrite.

### WR-07: The CR-01/CR-02 (and 27-11) fixes have zero automated regression coverage

**File:** `app/src/routes/admin/people/[id]/+page.svelte`

**Issue:** There is no unit, component, or e2e test anywhere in the reviewed file set that exercises the toggle-Bench-to-Advocate-then-save path, the merge-then-save path, or the person-id-change reset effect (the three code paths CR-01/CR-02/27-11 each specifically fixed). `svelte-check` and structural greps do not catch this class of bug — the original CR-01/CR-02 defects and the 27-11 infinite-loop regression were all silent-at-compile-time, runtime-only behaviors. A future edit to this file (the Person Type card has already been restructured once, per 27-09) could silently reintroduce any of the three with no automated signal.

**Fix:** Add a component/integration test (e.g., Playwright, or Vitest + Testing Library with mocked `fetch`) that renders the editor with a Justice fixture that has tenures/birthdate, toggles to Advocate, submits, and asserts the outgoing form body still carries the original tenure/birthdate values; and a second test that changes `data.person` (simulating navigation/merge redirect) and asserts `tenureRows`/`birthdate`/`isJustice` re-derive from the new person without throwing or looping.

### WR-08: Merge-preview fetch can race the person-change reset effect and briefly display stale data

**File:** `app/src/routes/admin/people/[id]/+page.svelte:153-172` (`fetchMergePreview`), `app/src/routes/admin/people/[id]/+page.svelte:125-151` (reset effect)

**Issue:** `fetchMergePreview` is an unguarded async function invoked from the merge `<select>`'s `onchange`. If an operator selects a merge target and then submits `save`/`photo`/`delete` before the preview fetch resolves, the resulting redirect reruns `load()` and reuses this component instance; the reset `$effect` fires and clears `mergePreview`/`mergeTargetId`/`mergeError`, but the in-flight `fetchMergePreview` promise is not cancelled. When it resolves afterward, its `.then`/`finally` continuation still unconditionally overwrites `mergePreview`/`mergeLoading`, even though `mergeTargetId` has since reset to `''` — the operator can briefly see merge-preview counts attributed to a target/person no longer selected.

**Fix:** Capture the request's originating `data.person.id`/`targetId` and ignore the response if either no longer matches current state when the fetch resolves:
```js
async function fetchMergePreview(targetId: string) {
    const requestPersonId = data.person.id;
    mergePreview = null;
    mergeError = null;
    if (!targetId) return;
    mergeLoading = true;
    try {
        const res = await fetch(`/admin/people/${requestPersonId}/merge-preview?target_id=${targetId}`);
        if (data.person.id !== requestPersonId || mergeTargetId !== targetId) return; // stale
        if (res.ok) mergePreview = await res.json();
        else mergeError = 'Could not load counts. Try again.';
    } catch {
        if (data.person.id === requestPersonId && mergeTargetId === targetId) {
            mergeError = 'Could not load counts. Try again.';
        }
    } finally {
        if (data.person.id === requestPersonId && mergeTargetId === targetId) mergeLoading = false;
    }
}
```

## Info

### IN-01: Orphaned Role schema/service/route left in place across three files

**File:** `api/schemas/admin_people.py:164-182`, `api/services/admin_people.py:499-519`, `api/routers/admin.py:1018-1034`

**Issue:** `RoleCreate`, `RoleResponse`, `create_role`, and `POST /api/admin/roles` are each marked `TODO(D-10): orphaned by Phase 27 — person-level roles removed; safe to delete once confirmed.` The plan that removed the only caller (the `createRole` form action) has already landed, so this is now confirmed-dead code rather than pending-confirmation code.

**Fix:** Delete `RoleCreate`/`RoleResponse` from the schema, `create_role` from the service, and the `POST /roles` route from the router together in a follow-up cleanup pass.

### IN-02: `list_participants_for_job` still joins the now-superseded person-level Role

**File:** `api/services/admin_people.py:702-742`

**Issue:** This function still does `.outerjoin(Role, Person.role_id == Role.id)` (line 725) and returns `role_name` on `ParticipantItem`. Per Phase 27 (D-10), person-level Role is superseded — `PersonCreateRequest`/`PersonUpdate` no longer expose `role_id` for writing, so for any person created or edited after Phase 27, `Person.role_id` can never be populated and `role_name` will always resolve to `None` for those rows. Harmless today (legacy rows may still have a value), but a future reader could mistake this for a still-maintained write path.

**Fix:** Add a short comment noting this is legacy-data-only, or remove the join once confirmed no legacy `role_id` data remains meaningful to this listing.

### IN-03: No schema-level (non-DB) unit test for `birthdate` or `PersonCreateRequest`'s name-part fields

**File:** `api/tests/test_admin_people_schemas_service.py`

**Issue:** The file thoroughly unit-tests `_missing_fields`, `_derive_full_name`, and several schema shapes, but there is no pure test asserting `PersonUpdate.birthdate` accepts an ISO string / defaults to `None`, or that `PersonCreateRequest` accepts/omits the four Phase 27 Plan 08 name-part fields at the schema layer — the only coverage for the latter is the two DB-guarded tests flagged in WR-04, which are typically skipped when `DATABASE_URL` is unset.

**Fix:** Add lightweight schema-only tests, e.g. `PersonUpdate(birthdate="1955-01-27").birthdate == "1955-01-27"` and `PersonCreateRequest(full_name="X", is_justice=True).first_name is None`.

### IN-04: `update_person`/`_replace_tenures` docstrings overstate the "no write happens before validation" guarantee

**File:** `api/services/admin_people.py:386-388, 136-140`

**Issue:** `update_person`'s docstring claims a malformed tenure date "raises ValueError... before any DB write completes." In practice, by the time `_replace_tenures` runs, every other field has already been mutated on the ORM-tracked `person` object, and `_replace_tenures` itself issues `DELETE FROM court_tenures` (lines 136-140) before parsing/inserting the new rows. Whether that `DELETE` is actually rolled back on a later `ValueError` depends entirely on the `get_db` session dependency's exception-exit behavior, not on anything in this function — the same commit/rollback-boundary fragility flagged more concretely in WR-05.

**Fix:** Tighten the docstring wording to "no commit occurs," or reorder `_replace_tenures` to validate/parse all dates before issuing the `DELETE`.

### IN-05: Inconsistent HTTP-status handling across the `[id]`/`new` SvelteKit form actions

**File:** `app/src/routes/admin/people/[id]/+page.server.ts:189-191, 255-262`, `app/src/routes/admin/people/new/+page.server.ts:98-100`

**Issue:** The `merge` action correctly distinguishes the backend's actual status code (`fail(res.status === 422 ? 422 : 502, ...)`), but the `save` action, the `photo` action's non-422 branch, and the `new` route's `create` action all collapse every `!res.ok` response — whether the backend actually returned 422, 500, or something else — into a single fixed status with a generic message. Not a functional bug, but it makes backend 5xx failures indistinguishable from legitimate validation failures in what the operator (and any status-code-based monitoring) sees.

**Fix:** Mirror the `merge` action's `res.status === 422 ? 422 : 502` pattern in `save`, `photo`, and `create` for consistency.

### IN-06: `delete_block_count` is computed and returned by `load()` but never consumed

**File:** `app/src/routes/admin/people/[id]/+page.server.ts:96, 108, 114`

**Issue:** `delete_block_count` is derived from the merge-preview counts and returned in `load()`'s data, but `[id]/+page.svelte`'s delete section only reads `data.can_delete` and renders a static, count-free message ("Cannot delete — this person has associated records and cannot be removed."). The computed value is currently dead as far as the UI is concerned.

**Fix:** Either surface it in the disabled-state copy (e.g., "Cannot delete — N associated record(s)."), or remove the computation and the field from the returned data shape.

---

_Reviewed: 2026-07-09_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
