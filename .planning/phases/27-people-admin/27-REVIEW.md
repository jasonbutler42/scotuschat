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
  critical: 0
  warning: 7
  info: 5
  total: 12
status: issues_found
---

# Phase 27: Code Review Report

**Reviewed:** 2026-07-09
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

This review covers the full, final state of Phase 27 (`27-people-admin`) after gap-closure plan `27-10`, which claimed to fix two BLOCKER data-loss defects (CR-01/CR-02) from the prior review pass. Both fixes were verified by direct inspection and are **confirmed correct and complete** — no new Critical findings were raised.

**CR-01 verification (fixed):** In `app/src/routes/admin/people/[id]/+page.svelte`, the hidden `birthdate` input (line 498) and the hidden `tenures` input (line 499) now sit immediately before `{#if isJustice}` (line 501), alongside the pre-existing always-present `is_justice` hidden input (line 492) — all three carry `form="save-form"` and are no longer nested inside the toggle's conditional block. The visible Birth Date `<input type="date">` (lines 512-517) now has no `name`/`form` attribute — it is a pure `bind:value` UI control and no longer duplicates the submitted `birthdate` key. There is exactly one `name="birthdate"` input and exactly one `name="tenures"` input in the file. Because `birthdate` and `tenureRows` are `$state` variables that are never cleared when the Bench/Advocate toggle flips, toggling an existing Justice to "Advocate" and clicking "Save Person" now submits the operator's real, current tenure/birthdate state instead of the toggle's absent-defaults (`null` / `[]`) — the data-destruction path described in the prior CR-01 finding is closed.

**CR-02 verification (fixed):** The person-id-change reset `$effect` (lines 125-150) now additionally sets `nextKey = 1` (line 133) and re-derives `tenureRows` from `data.person.tenures` (lines 134-149), mirroring the top-of-script initializer's mapping field-for-field. Because this effect also reads `data.person.is_justice`/`data.person.birthdate`/`data.person.tenures` during execution (not just `data.person.id`), it is a dependency of all of those reactive reads, so it reliably re-runs whenever the underlying person data changes — including the post-merge redirect to `/admin/people/{target_id}` that was the concrete scenario in the original finding. A Save immediately after a merge redirect will now write the target person's real tenure rows, not a stale array carried over from the previously-viewed source person.

No new BLOCKER-severity issues were found in this pass. However, several Warning/Info items from the prior review remain open (the plan explicitly scoped `27-10` to only the two Critical fixes and excluded everything else), and this pass surfaces a few additional Warning/Info items — most notably a pre-existing full-name auto-derivation behavior in `update_person` that silently discards a manually-typed "Full name" value, and the observation that the just-verified CR-01/CR-02 fixes have zero automated regression coverage (the behavioral round-trip was explicitly deferred to manual UAT).

## Warnings

### WR-01: Merge-target picker never renders "Last, First" — dead client-side fields (carried forward, still unfixed)

**File:** `app/src/routes/admin/people/[id]/+page.server.ts:39-44`, `app/src/routes/admin/people/[id]/+page.svelte:721-725`
**Issue:** The local `PersonListItem` TypeScript interface declares `last_name`/`first_name`, and the merge-target `<select>` reads them:
```svelte
{p.last_name ? `${p.last_name}, ${p.first_name ?? ''}` : p.full_name}
```
The server's `PersonListItem` Pydantic schema (`api/schemas/admin_people.py:47-71`) has no `first_name`/`last_name` fields, so `GET /api/admin/people` never returns them — `p.last_name` is always `undefined` and the ternary always falls through to `p.full_name`. This was flagged in the prior review and is still present unchanged.
**Fix:** Either add `first_name`/`last_name` to the server `PersonListItem` schema/`list_people` output, or drop the dead branch and the two unused interface fields client-side.

### WR-02: Photo-by-URL fetch has no host allowlist, unlike the sibling PDF-URL validator (carried forward, still unfixed)

**File:** `api/routers/admin.py:741-763`
**Issue:** `_validate_pdf_url` restricts ingest URLs to `https://…supremecourt.gov` specifically to mitigate SSRF (T-07-01). The photo-by-URL path in `upload_person_photo` only checks the scheme:
```python
_parsed_url = _urlparse(photo_url)
if _parsed_url.scheme != 'https':
    raise HTTPException(status_code=422, detail="Photo URL must use HTTPS.")
...
r = await client.get(photo_url, follow_redirects=False)
```
Any admin-authenticated request can direct the server to issue an HTTPS GET to an arbitrary host (internal services, cloud metadata endpoints reachable over HTTPS, etc.) — the request completes before the Pillow validation ever runs. Given this project's stated compliance posture (CIS Controls, cyber-insurance expectations around SSRF-class findings), this remains worth closing.
**Fix:** Apply the same allowlist discipline used for `_validate_pdf_url`, or at minimum reject requests that resolve to private/link-local/loopback address ranges before issuing the `httpx` GET.

### WR-03: Overly broad exception handling in image validation masks unrelated failures (carried forward, still unfixed)

**File:** `api/routers/admin.py:732, 758`
**Issue:** Both image-validation blocks use `except (UnidentifiedImageError, Exception):`. Since `Exception` is already a superset of `UnidentifiedImageError`, the more specific exception is redundant dead code, and the broad catch-all also swallows unrelated bugs (a stray `TypeError`, an `OSError` mid-read, an out-of-memory condition on a huge upload, etc.), surfacing them to the operator as a generic "not a valid image" 422 and discarding the real cause server-side.
**Fix:** Narrow to the exceptions Pillow actually documents for `Image.open`/`.verify()` (`UnidentifiedImageError`, `OSError`), and log the original exception server-side before returning the generic 422.

### WR-04: Gap-closure DB tests are effectively unreachable in CI (carried forward, still unfixed)

**File:** `api/tests/test_admin_people_schemas_service.py:380-383`
**Issue:**
```python
def _db_configured() -> bool:
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"
```
The `"sk-ant" not in url` check (an Anthropic API-key prefix substring) has no relationship to a Postgres/asyncpg connection string and reads as a copy/paste artifact. Unless the CI environment explicitly sets a real `DATABASE_URL`, both `test_create_person_persists_name_parts_when_supplied` and `test_create_person_leaves_name_parts_none_when_omitted` are skipped by default, leaving UAT Gap 3's fix without automated coverage.
**Fix:** Remove the unrelated `"sk-ant"` check; confirm CI actually sets `DATABASE_URL` so these tests run, or move the pure "name parts persist/omit" assertions into a lighter test that doesn't require a live database.

### WR-05: `delete_person_if_orphan` deletes SpeakerAlias rows before the orphan check completes, relying entirely on implicit session-rollback-on-close

**File:** `api/services/admin_people.py:597-636`
**Issue:** The function unconditionally issues `DELETE FROM speaker_alias WHERE person_id = :id` (lines 612-617) *before* checking whether the person actually has zero rows in `Utterance`/`CaseAppearance`/`ArgumentParticipant`. If any of those three counts is nonzero, the function returns `False` at line 628 without calling `db.commit()` and without any explicit `db.rollback()`. Correctness here depends entirely on `get_db`'s `async with AsyncSessionLocal() as session: yield session` pattern (`api/core/database.py`) discarding uncommitted work when the session closes at request teardown — nothing in this function's own structure prevents a partial, silent alias deletion if that assumption ever changes (e.g., a future refactor adds an intermediate `db.commit()`, switches to autocommit-style session handling, or another code path elsewhere in the same request commits first). This is the same "commit/rollback boundary" fragility already called out in IN-05 below, but here it directly precedes a 409-returning guard rather than a 422-returning one, so the blast radius is larger — a "cannot delete, has records" response should never itself be the trigger for silently discarding one of those records' inputs (the person's SpeakerAlias rows).
**Fix:** Move the count checks (lines 619-628) before the `SpeakerAlias` delete, or wrap the whole sequence in an explicit transaction with a `try/except` that rolls back before returning `False`.

### WR-06: `update_person`'s full-name auto-derivation silently discards a manually-edited "Full name" value

**File:** `api/services/admin_people.py:436-445`
**Issue:**
```python
if body.first_name and body.last_name:
    person.full_name = _derive_full_name(
        body.first_name, body.middle_name, body.last_name, body.name_suffix,
    )
```
The `[id]` editor's `save` action always sends `first_name`/`last_name` (trimmed, or `null`) alongside `full_name` in every submission (`app/src/routes/admin/people/[id]/+page.server.ts:137-140, 177-183`) — they are not split across separate forms the way `bio_text`/`photo_url` are. Consequently, for any person who already has both `first_name` and `last_name` populated (the common case for anyone past initial data entry), **every** Save Person click recomputes `full_name` from the structured parts and overwrites whatever string the operator typed directly into the "Full name" text box — even if that edit was intentionally different from the mechanical `first + middle + last + suffix` concatenation (a nickname, a stage name, a historical spelling variant, etc.). The UI presents "Full name" as a freely editable field with no indication that it is derived/read-only whenever the name-part fields are populated.
**Fix:** Either make "Full name" genuinely authoritative (drop the auto-derivation, or only derive it when the operator hasn't also changed `full_name` directly in the same submission), or make the UI honestly reflect the derived nature of the field (e.g., disable it, or show a note that it is computed from the parts below) so this isn't a silent overwrite.

### WR-07: The CR-01/CR-02 gap-closure fixes have zero automated regression coverage

**File:** `app/src/routes/admin/people/[id]/+page.svelte`, `.planning/phases/27-people-admin/27-10-PLAN.md:88-96, 121-126`
**Issue:** Both `27-10` tasks' `<acceptance_criteria>` explicitly defer the actual behavioral verification ("toggle Bench→Advocate, Save, reload — tenure/birthdate preserved"; "merge A into B, Save on B, reload — B's tenures are B's own") to a future manual "Phase 27 UAT retest." The only automated gates are `svelte-check` plus grep-based structural checks (input position, input-name uniqueness). There is no unit, component, or e2e test anywhere in the reviewed file set that exercises the toggle-then-save or merge-then-save code paths. Since this is precisely the class of bug that was just fixed (a silent, no-error-thrown data-loss path), and nothing in CI would catch a regression, a future edit to this file (e.g., restructuring the Person Type card again, as `27-09` already did once) could silently reintroduce either CR-01 or CR-02 with no automated signal.
**Fix:** Add a component/integration test (e.g., Playwright or Vitest + Testing Library) that renders the editor with a Justice fixture that has tenures/birthdate, toggles to Advocate, submits, and asserts the outgoing `FormData` (or mocked fetch body) still contains the original tenure/birthdate values; a second test covering the id-change/merge-reset effect re-deriving `tenureRows` from new `data.person.tenures`.

## Info

### IN-01: Orphaned Role schema/service/route left in place across three files (carried forward)

**File:** `api/schemas/admin_people.py:164-182`, `api/services/admin_people.py:499-519`, `api/routers/admin.py:1018-1034`
**Issue:** `RoleCreate`, `RoleResponse`, `create_role`, and `POST /api/admin/roles` are each marked `TODO(D-10): orphaned by Phase 27 — person-level roles removed; safe to delete once confirmed.` The plan that removed the only caller (the `createRole` form action) has landed, so this is now confirmed-dead code.
**Fix:** Delete `RoleCreate`/`RoleResponse` from the schema, `create_role` from the service, and the `POST /roles` route from the router in a follow-up cleanup pass.

### IN-02: `list_participants_for_job` still joins the now-superseded person-level Role (carried forward)

**File:** `api/services/admin_people.py:702-742`
**Issue:** This function still does `.outerjoin(Role, Person.role_id == Role.id)` (line 725) and returns `role_name` on `ParticipantItem`. Per Phase 27 (D-10), person-level Role is superseded — `PersonCreateRequest`/`PersonUpdate` no longer expose `role_id` for writing, so for any person created or edited after Phase 27, `Person.role_id` can never be populated and `role_name` will always resolve to `None`. Harmless today, but a future reader could mistake this for a still-live write path.
**Fix:** Add a short comment noting this is legacy-data-only, or remove the join once confirmed no legacy `role_id` data remains meaningful.

### IN-03: No schema-level (non-DB) unit test for `birthdate` or `PersonCreateRequest`'s name-part fields (carried forward)

**File:** `api/tests/test_admin_people_schemas_service.py`
**Issue:** The file thoroughly unit-tests `_missing_fields`, `_derive_full_name`, and several schema shapes, but there is no pure test asserting `PersonUpdate.birthdate` defaults to `None`/accepts an ISO string, or that `PersonCreateRequest` accepts/omits the four Phase 27 Plan 08 name-part fields at the schema layer — the only coverage for the latter is the two DB-guarded tests flagged in WR-04, which are typically skipped.
**Fix:** Add lightweight schema-only tests, e.g. `PersonUpdate(birthdate="1955-01-27").birthdate == "1955-01-27"` and `PersonCreateRequest(full_name="X", is_justice=True).first_name is None`.

### IN-04: `update_person`/`_replace_tenures` docstrings overstate the "no write happens before validation" guarantee (carried forward)

**File:** `api/services/admin_people.py:386-388, 131-134`
**Issue:** `update_person`'s docstring claims a malformed tenure date "raises ValueError... before any DB write completes" (lines 386-388). In practice, by the time `_replace_tenures` runs, every other field has already been mutated on the ORM-tracked `person` object, and `_replace_tenures` itself issues the `DELETE FROM court_tenures` statement (lines 136-140) before parsing/inserting new rows. Whether that `DELETE` is actually rolled back depends entirely on the `get_db` session dependency's exception-exit behavior, not on anything in this function — the same commit/rollback-boundary fragility flagged more concretely in WR-05.
**Fix:** Tighten the wording to "no commit occurs," or reorder `_replace_tenures` ahead of the other field mutations so the ordering matches the documented intent.

### IN-05: Inconsistent HTTP-status handling across the `[id]`/`new` SvelteKit form actions

**File:** `app/src/routes/admin/people/[id]/+page.server.ts:189-191, 255-262`, `app/src/routes/admin/people/new/+page.server.ts:98-100`
**Issue:** The `merge` action correctly distinguishes the backend's actual status code (`fail(res.status === 422 ? 422 : 502, ...)`, lines 296-300 of `[id]/+page.server.ts`), but the `save` action (lines 189-191), the `photo` action's non-422 branch (line 261), and the `new` route's `create` action (lines 98-100) all collapse every `!res.ok` response — whether the backend actually returned 422, 500, or something else — into a single fixed status (`422` or `502`) with a generic message. This is a minor inconsistency in how backend failures are surfaced, not a functional bug, but it makes backend-side 5xx failures indistinguishable from legitimate validation failures in the response the operator (and any monitoring on response codes) sees.
**Fix:** Mirror the `merge` action's `res.status === 422 ? 422 : 502` pattern in `save`, `photo`, and `create` for consistency.

---

_Reviewed: 2026-07-09_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
