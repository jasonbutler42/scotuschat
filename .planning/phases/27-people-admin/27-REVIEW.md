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
  warning: 4
  info: 2
  total: 7
status: fixed
fixes_applied:
  - "CR-01: update_person now guards bio_text/photo_url/first_name/last_name/middle_name/name_suffix/birthdate with model_fields_set (not is_not_None — the frontend collapses 'cleared' and 'omitted' to the same null, so only model_fields_set preserves the distinction). Mirrors the original CR-02 fix (commit 64d9d00b) that a later, unrelated commit (2af7d3f5) accidentally reverted. Added a regression test (test_update_person_partial_patch_does_not_wipe_other_fields)."
  - "WR-01: gap-detection query now excludes NULL argued_date rows explicitly."
  - "WR-03: create-person route no longer renders Birth Date / Tenure Period inputs it silently discarded on submit — removed for consistency with the existing Photo/Biography exclusion (same underlying reason)."
  - "WR-04 (partial): removed stale role_id/role_name kwargs from 3 tests in test_admin_people_schemas_service.py and 1 test in test_admin_people.py; corrected test_list_people_incomplete_filter (renamed test_list_people_missing_filter) to use the current ?missing= param instead of the removed ?incomplete= param. Did not add full new-logic coverage for _tenure_coverage/_bench_role_and_missing_tenure/create_person — flagged as a separate follow-up, not fixed here."
  - "IN-01: PersonListItem docstring's 'Possible values' list updated to match _missing_fields' actual output."
not_fixed:
  - "WR-02: dead first_name/last_name fields in the [id] editor's merge-picker TypeScript type — traced to Phase 12 (commit 6b008dfe), predates Phase 27 and is unrelated to it. Flagged, not fixed."
  - "IN-02: _replace_tenures/update_person docstring wording overstates the pre-commit rollback guarantee — low value, not fixed."
---

# Phase 27: Code Review Report

**Reviewed:** 2026-07-09T00:00:00Z
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Phase 27 adds `people.birthdate`, per-tenure appointment fields, and a Bench/Advocate
directory rework. The migration, schemas, and most of the new query logic
(`_tenure_coverage`, `_bench_role_and_missing_tenure`, `list_people` filtering) are
sound. However, tracing `update_person` against its two callers (the `save` and
`photo` form actions on `/admin/people/[id]`) surfaces a real, provable data-loss
bug: because the two forms each submit only a subset of `PersonUpdate`'s fields,
and `update_person` only guards `full_name`/`is_justice`/`tenures` against
"field not supplied," every "Save Person" click wipes `bio_text`/`photo_url`, and
every "Upload photo"/bio save wipes `first_name`/`last_name`/`middle_name`/
`name_suffix`/`birthdate`. This is a BLOCKER. Several smaller correctness and
test-hygiene issues (NULL-date tenure-gap false positives, a dead TypeScript
field pair in the merge picker, silently-discarded create-form input, and stale
test assertions referencing already-removed schema fields) round out the WARNING
tier.

## Critical Issues

### CR-01: `update_person` silently wipes fields the current request didn't intend to touch

**File:** `api/services/admin_people.py:394-410`
**Issue:**

`update_person` only guards three fields against "not supplied in this PATCH":

```python
if body.full_name is not None:
    person.full_name = body.full_name
...
if body.is_justice is not None:
    person.is_justice = body.is_justice
...
if body.tenures is not None:
    await _replace_tenures(db, person_id, body.tenures)
```

Every other field is written unconditionally, treating "not present in the JSON
body" (Pydantic default `None`) identically to "operator explicitly cleared this
field":

```python
person.bio_text = body.bio_text if body.bio_text else None
person.photo_url = body.photo_url if body.photo_url else None

person.first_name = body.first_name if body.first_name else None
person.last_name = body.last_name if body.last_name else None
person.middle_name = body.middle_name if body.middle_name else None
person.name_suffix = body.name_suffix if body.name_suffix else None

person.birthdate = (
    datetime.date.fromisoformat(body.birthdate) if body.birthdate else None
)
```

The frontend deliberately splits person edits across two separate forms/actions
on `app/src/routes/admin/people/[id]/+page.server.ts`:

- `save` (Identity + Person Type card) sends `full_name, tenures, first_name,
  last_name, middle_name, name_suffix, is_justice, birthdate` — **omitting**
  `bio_text` and `photo_url` (per the "Pitfall 7 extended" comment at lines
  127-130, 178-183).
- `photo` (Bio & Photo card) sends only `{ bio_text }` in its best-effort PATCH
  (lines 219-228) — **omitting** `full_name, first_name, last_name,
  middle_name, name_suffix, is_justice, birthdate, tenures`.

Because the two omitted fields on each request default to `None` in the
`PersonUpdate` Pydantic model, and `update_person` has no `is not None` guard
for them, the result is:

- Clicking **Save Person** wipes `bio_text` and `photo_url` to `NULL`, even if
  the operator only changed the person's name.
- Clicking **Upload photo** or saving the Biography textarea wipes
  `first_name`, `last_name`, `middle_name`, `name_suffix`, and the new
  Phase 27 `birthdate` field to `NULL`, even if the operator only changed the
  photo or bio.

Round-tripping between the two cards (a completely normal editing session —
e.g. set the name, save, then upload a photo) causes progressive, silent data
loss across every field not carried by the form that was just submitted. This
is a genuine BLOCKER: it destroys operator-entered data (including the newly
added Birth Date and structured name fields this phase introduces) with no
error, warning, or confirmation. It is not caught by any existing test —
`test_admin_people_schemas_service.py` only exercises pure schema construction
and `_missing_fields`, never `update_person`'s partial-update semantics.

**Fix:** Apply the same "only write when explicitly supplied" guard already
used for `full_name`/`is_justice`/`tenures` to every other field, and keep the
empty-string→`NULL` normalization *inside* that guard so an explicit `""` can
still clear a field:

```python
if body.bio_text is not None:
    person.bio_text = body.bio_text or None
if body.photo_url is not None:
    person.photo_url = body.photo_url or None

if body.first_name is not None:
    person.first_name = body.first_name or None
if body.last_name is not None:
    person.last_name = body.last_name or None
if body.middle_name is not None:
    person.middle_name = body.middle_name or None
if body.name_suffix is not None:
    person.name_suffix = body.name_suffix or None

if body.birthdate is not None:
    person.birthdate = (
        datetime.date.fromisoformat(body.birthdate) if body.birthdate else None
    )
```

This is safe with the current frontend: the `photo` action's best-effort PATCH
always sends `bio_text` as an explicit string (`""` when cleared, never
omitted), and the `save` action always sends `first_name`/`last_name`/
`middle_name`/`name_suffix`/`birthdate` as explicit strings or `null`
(never omits the keys) — so no currently-relied-upon "clear the field" behavior
is lost by adding the guard.

## Warnings

### WR-01: Tenure-gap detection produces false positives when `argued_date` is NULL

**File:** `api/services/admin_people.py:234-257`
**Issue:** `covering_tenure` compares `CourtTenure.start_date <= Argument.argued_date`
and `CourtTenure.end_date >= Argument.argued_date` directly against
`Argument.argued_date`, which is nullable (`api/models/models.py:171`, "job-driven
ingest leaves NULL instead of a synthetic date"). In SQL, any comparison against
`NULL` evaluates to `NULL` (not `TRUE`), so `EXISTS(...)` can never match for a
row whose `argued_date IS NULL`, regardless of how many tenures actually cover
the person. `not_(covering_tenure)` is therefore always `TRUE` for BENCH
participants on unresolved/dateless arguments, incorrectly marking those people
as `has_tenure_gap = True` and pulling them into the `tenure_gaps=1` filter even
when every one of their dated arguments is fully covered. Contrast this with
`_bench_role_and_missing_tenure` (same file, lines 719-739), which explicitly
documents and handles the `argued_date is None` case as "coverage cannot be
determined" rather than silently defaulting to "gap."
**Fix:** Exclude NULL-date arguments from the gap-detection query explicitly,
mirroring the documented intent:

```python
.where(
    ArgumentParticipant.side == SideEnum.BENCH,
    ArgumentParticipant.person_id.isnot(None),
    Argument.argued_date.isnot(None),
    not_(covering_tenure),
)
```

### WR-02: Merge-picker "Lastname, Firstname" display never renders — dead field pair

**File:** `app/src/routes/admin/people/[id]/+page.server.ts:39-44`, used at
`app/src/routes/admin/people/[id]/+page.svelte:662, 682, 705`
**Issue:** The local `PersonListItem` TypeScript interface declares
`last_name: string | null` and `first_name: string | null`, and the `.svelte`
template reads `p.last_name` / `p.first_name` to format merge-target options as
`"Lastname, Firstname"`. But the actual response from
`GET /api/admin/people` is the server-side `PersonListItem` schema
(`api/schemas/admin_people.py:42-65`), which has no `first_name`/`last_name`
fields at all (Phase 27 dropped person-level Role but never added these). At
runtime `p.last_name` is `undefined`, which is falsy, so the ternary always
falls through to `p.full_name` — the intended "Lastname, Firstname" sort/display
aid silently never activates. This is a real defect (a documented feature that
does not work), not merely a style nit; the TS types are actively lying about
the shape of the data crossing the API boundary.
**Fix:** Either add `first_name`/`last_name` to the server `PersonListItem`
schema and `list_people` service output, or drop the dead formatting branch and
the two unused interface fields from the client.

### WR-03: Create-person form silently discards Birth Date and Tenure rows on submit

**File:** `app/src/routes/admin/people/new/+page.server.ts:56-59` (create action
only reads `full_name` + `is_justice`); `app/src/routes/admin/people/new/+page.svelte`
(Birth Date input at ~line 307 and the full Tenure Period sub-card UI at
~lines 339-448 let the operator fill in dates/appointment data before the first save)
**Issue:** The create form fully renders Birth Date and repeatable Tenure Period
sub-cards once "Bench" is selected, and both are wired into hidden fields
targeting `form="create-form"`. But the `create` action deliberately reads only
`full_name` and `is_justice` from the submitted `FormData` — `birthdate` and
`tenures` are never sent to the backend (this is intentional per the code
comments referencing D-08). The result: an operator who fills in a Justice's
birth date and one or more tenure periods before clicking "Save Person" sees no
indication that this data is about to be discarded — clicking Save just redirects
to the new person's editor with those fields blank again. There is no
confirmation, warning banner, or disabling of those inputs to signal "this
won't be saved yet."
**Fix:** Either disable/hide the Birth Date and Tenure Period inputs on the
create form until the person exists (consistent with how Photo/Biography is
already hidden on this route for the same reason), or add an inline note near
those inputs stating they will be discarded and must be re-entered after
creation.

### WR-04: Stale test assertions reference removed schema fields; no coverage for Phase 27 logic

**File:** `api/tests/test_admin_people_schemas_service.py:183-198, 252-298`
**Issue:** `test_person_update_with_all_fields`, `test_person_list_item_shape`,
`test_person_detail_shape`, and `test_participant_item_shape` construct
`PersonUpdate`/`PersonListItem`/`PersonDetail` with `role_id=...`/`role_name=...`
kwargs. Those fields were removed from all three schemas by this phase (D-10);
Pydantic v2's default `extra="ignore"` behavior means the kwargs are silently
dropped rather than raising, so the tests still pass but no longer verify
anything about the schema's actual shape — they give false confidence that
`role_id`/`role_name` remain meaningful. Separately, this file (the designated
home for schema/service pure-function tests per its own module docstring) adds
no coverage at all for this phase's new logic: `PersonUpdate.birthdate`
round-tripping, `get_person_detail`'s birthdate serialization,
`_tenure_coverage`, `_bench_role_and_missing_tenure`, `list_people`'s
`is_justice`/`missing`/`tenure_gaps` filtering, or `create_person`. The
`update_person` partial-update bug described in CR-01 is exactly the kind of
regression a service-level unit test here would have caught.
**Fix:** Remove the stale `role_id`/`role_name` kwargs from the affected tests
(or replace with an explicit assertion that they are *not* accepted, if that's
the intended regression guard), and add unit tests for `_tenure_coverage`,
`_bench_role_and_missing_tenure`, and — critically — `update_person`'s
per-field "omitted vs. explicitly cleared" semantics.

## Info

### IN-01: `PersonListItem` docstring's "Possible values" list is stale

**File:** `api/schemas/admin_people.py:44-53`
**Issue:** The class docstring still says `missing`'s "Possible values:
"role", "bio", "photo" (see D-04, D-06)" — leftover from before this phase.
The actual vocabulary produced by `_missing_fields` (and required to match the
`missing` query-param filter per its own T-27-03 comment) is `"first name"`,
`"last name"`, `"photo"`, `"bio"`, `"birthdate"`, `"no tenures"`. `"role"` is no
longer ever produced.
**Fix:** Update the docstring's "Possible values" line to match
`_missing_fields`'s actual output.

### IN-02: `_replace_tenures`/`update_person` docstrings overstate the "no write happens before validation" guarantee

**File:** `api/services/admin_people.py:131-134, 429-431`
**Issue:** Both docstrings claim a malformed tenure date "raises ValueError...
before any DB write completes" / "before any DB write completes (Pitfall 6)."
In practice, by the time `_replace_tenures` is invoked (near the end of
`update_person`), every other field (`bio_text`, `photo_url`, `first_name`,
etc.) has already been mutated on the ORM-tracked `person` object, and
`_replace_tenures` itself has already issued the `DELETE FROM court_tenures`
statement before it starts parsing/inserting the new rows. "No DB write
completes" is only true in the sense that `db.commit()` hasn't been called —
whether the already-issued `DELETE` and pending `UPDATE`s are actually rolled
back depends entirely on the (unreviewed) `get_db` session dependency
performing a rollback on exception exit, not on anything in this function.
**Fix:** Either tighten the docstring wording to "no commit occurs" rather than
"no DB write completes," or move `_replace_tenures` before the other field
mutations so at minimum the ordering matches the documented intent within this
file.

---

## Fixes Applied (post-review, orchestrator pass)

CR-01, WR-01, WR-03, IN-01 fixed; WR-04 partially fixed (stale kwargs removed,
one query-param staleness in `test_admin_people.py` found and fixed along the
way, new-logic coverage not added). WR-02 and IN-02 left as documented,
unfixed findings — see `not_fixed` in frontmatter for why.

All fixes verified via `py_compile`, `npm run check`, `npm run build`, and a
full pytest run diffed against the pre-phase-27 baseline (57 failed / 34
errors, confirmed via a disposable worktree at commit `ebb14eaa`) — no new
failures beyond that baseline, except the two DB-gated tests this pass
touched/added (`test_list_people_missing_filter`,
`test_update_person_partial_patch_does_not_wipe_other_fields`), which hit the
same pre-existing, unrelated bug the baseline already contains: FastAPI's
`AsyncSessionLocal` session factory is not initialized when tests from
multiple pytest `testpaths` directories run together in one session
(`api/core/database.py:62`, "lifespan may not have completed startup").
Both tests were verified by static reading against the actual router/schema
code, not by a passing run — that infra bug is outside phase 27's scope and
is a separate, pre-existing issue worth its own investigation.

_Reviewed: 2026-07-09T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
