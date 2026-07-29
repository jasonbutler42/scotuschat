---
phase: 38-full-name-vs-name-parts-rethink
reviewed: 2026-07-27T17:02:14Z
depth: standard
files_reviewed: 33
files_reviewed_list:
  - alembic/versions/0022_person_name_authority.py
  - api/domain/__init__.py
  - api/domain/person_names.py
  - api/models/models.py
  - api/routers/admin.py
  - api/schemas/admin_jobs.py
  - api/schemas/admin_people.py
  - api/services/admin_jobs.py
  - api/services/admin_people.py
  - api/tests/fixtures/person_name_cases.json
  - api/tests/test_admin_jobs_phase25.py
  - api/tests/test_admin_people.py
  - api/tests/test_admin_people_schemas_service.py
  - api/tests/test_isolation_survives_inner_commit.py
  - api/tests/test_migration_0022_person_name_authority.py
  - api/tests/test_person_names.py
  - api/tests/test_phase38_extracted_value_contract.py
  - api/tests/test_phase38_people_ui_contract.py
  - app/src/lib/components/CopyableExtractedValue.svelte
  - app/src/lib/components/DocketPillInput.svelte
  - app/src/lib/components/ResolveCard.svelte
  - app/src/lib/personNames.ts
  - app/src/routes/admin/arguments/[id]/+page.svelte
  - app/src/routes/admin/people/+page.server.ts
  - app/src/routes/admin/people/+page.svelte
  - app/src/routes/admin/people/[id]/+page.server.ts
  - app/src/routes/admin/people/[id]/+page.svelte
  - app/src/routes/admin/people/new/+page.server.ts
  - app/src/routes/admin/people/new/+page.svelte
  - app/src/routes/admin/pipeline/[job_id]/+page.svelte
  - pipeline/commands/import_convokit.py
  - pipeline/commands/import_justices_csv.py
  - pipeline/commands/seed_aliases.py
  - pipeline/tests/test_import_convokit_core.py
  - pipeline/tests/test_import_justices_csv.py
  - pipeline/tests/test_seed_aliases.py
findings:
  critical: 1
  warning: 3
  info: 2
  total: 6
status: issues_found
---

# Phase 38: Code Review Report

**Reviewed:** 2026-07-27T17:02:14Z
**Depth:** standard
**Files Reviewed:** 33 (listed above; `api/domain/__init__.py` is empty)
**Status:** issues_found

## Summary

Phase 38 replaces `full_name` with structured name parts as the operator-editable
authority, adds a conservative legacy-name splitter, a durable `name_needs_review`
flag, and an independent `name_extraction_metadata` provenance envelope, all wired
through a shared `api.domain.person_names` module consumed by the API services,
three pipeline commands, and a TypeScript parity mirror. The domain module itself
(`split_legacy_full_name`, `prepare_person_name`, `prepare_name_provenance`) is well
factored, pure, and heavily fixture-tested, and the mass-assignment/`extra="forbid"`
discipline on the write schemas is applied consistently.

However, the migration that performs the one-time legacy backfill (0022) contains a
genuine correctness bug in its own safety gate: the "round-trip" check that is
supposed to prevent a lossy split from ever being persisted instead **causes the
entire migration to abort** on any legacy row whose `full_name` has leading or
trailing whitespace — even though such a row is exactly the kind of confident,
lossless split the migration is designed to auto-apply. This is a data-migration
correctness/availability bug (BLOCKER). Two further items are flagged as warnings
(an unverified `AttributeError` risk on an existing response schema this phase's
services now feed data through, and a stale non-functional link introduced/left in
a Phase-38-adjacent template), plus two minor info items.

## Critical Issues

### CR-01: Migration 0022's round-trip abort gate compares against the wrong string, aborting the entire migration on legacy rows with leading/trailing whitespace

**File:** `alembic/versions/0022_person_name_authority.py:107-141`

**Issue:**

The backfill loop reads the raw, un-stripped column value into `pre_full_name`:

```python
pre_full_name = row.full_name
...
result = split_legacy_full_name(pre_full_name)
```

Inside `split_legacy_full_name` (`api/domain/person_names.py:289-367`), the function
strips the input once (`stripped = full_name.strip()`) and bases its own
`auto_apply`/round-trip decision on `candidate_full_name == stripped` — i.e. it
correctly treats a leading/trailing-whitespace legacy value such as
`"  John Roberts  "` as a High-confidence, exact-round-trip, two-token split
(`first="John"`, `last="Roberts"`).

Back in the migration, when `result.auto_apply` is `True`, a *second* round-trip
check re-derives the candidate and compares it against the **un-stripped**
`pre_full_name`, not the trimmed value:

```python
if result.auto_apply:
    recomputed = format_full_name(
        result.first_name, result.middle_name, result.last_name, result.name_suffix,
    )
    if recomputed != pre_full_name:
        raise RuntimeError(
            f"people.id={row.id}: split round-trip mismatch "
            f"({recomputed!r} != {pre_full_name!r}) — aborting "
            "migration 0022 rather than persist a lossy split."
        )
```

For `pre_full_name = "  John Roberts  "`, `recomputed = "John Roberts"` (no
surrounding whitespace, since `format_full_name` joins already-normalized parts).
`"John Roberts" != "  John Roberts  "` is `True`, so this **raises `RuntimeError`
and aborts the entire migration** — not just skips or flags this one row. Per the
migration's own docstring, "Postgres transactional DDL rolls the entire migration
back (schema and data) on any such abort," meaning a single legacy row with
trivial leading/trailing whitespace (a very plausible occurrence in
scraped/PDF-derived or CSV-imported legacy `full_name` values) makes migration 0022
**entirely inapplicable** to that database until the data is manually fixed outside
the documented backfill/review path — even though `split_legacy_full_name` itself
correctly and safely handles the case.

This is a genuine logic bug, not a deliberate strictness choice: the two round-trip
checks (inside `split_legacy_full_name` and inside the migration) are supposed to
agree on what "exact round trip" means, and they don't. `full_name` itself is never
rewritten by this migration regardless (by design), so there is no reason the
second gate needs to be stricter than the first.

No test in `api/tests/test_migration_0022_person_name_authority.py` or
`api/tests/fixtures/person_name_cases.json` exercises a `full_name` value with
leading/trailing whitespace, so this defect is currently untested and unguarded.

**Fix:**

```python
pre_full_name = row.full_name
if pre_full_name is None or not pre_full_name.strip():
    raise RuntimeError(...)

stripped_full_name = pre_full_name.strip()
result = split_legacy_full_name(pre_full_name)
...
if result.auto_apply:
    recomputed = format_full_name(
        result.first_name, result.middle_name, result.last_name, result.name_suffix,
    )
    if recomputed != stripped_full_name:
        raise RuntimeError(...)
```

Add a regression fixture (`legacy_split_cases` or a dedicated migration test) for a
`full_name` such as `"  Clarence Thomas  "` asserting the row is auto-applied
(`name_needs_review=False`, parts populated) and the migration does **not** abort,
while `full_name` itself is still preserved byte-for-byte including its original
whitespace.

## Warnings

### WR-01: `create_person_for_job`'s `PersonResponse.role_name` field has no backing attribute on `Person`, risking an unhandled `AttributeError` at response-serialization time

**File:** `api/schemas/admin_jobs.py:123-131`, `api/services/admin_jobs.py:840-968`, `api/routers/admin.py:658-682`

**Issue:** `POST /api/admin/jobs/{job_id}/people` (`create_person_for_job`) returns a
raw `Person` ORM instance, serialized against `response_model=PersonResponse`:

```python
class PersonResponse(BaseModel):
    id: int
    full_name: str
    role_id: Optional[int] = None
    role_name: Optional[str] = None
    model_config = {"from_attributes": True}
```

`Person` (`api/models/models.py:103-133`) has a `role_id` FK column but **no**
`role_name` attribute anywhere (no column, no hybrid property). This same codebase
repeatedly documents, in this exact file's neighboring service (`admin_jobs.py`
lines 92-94, 147, 166, 285-291), that Pydantic's `from_attributes=True`
serialization raises `AttributeError` for a declared field with no corresponding
attribute on the source ORM object unless the attribute is explicitly injected
(`job.__dict__["parse_stats"] = None`, `job.__dict__.setdefault("is_archived", False)`,
`job.__dict__["source"] = ...`). `create_person_for_job` does no equivalent
injection for `role_name` before returning `person`, so if this observed
Pydantic/FastAPI behavior applies here too, every call to this endpoint would 500
with `AttributeError: 'Person' object has no attribute 'role_name'` rather than
returning `PersonResponse`.

No test in the reviewed files exercises this endpoint through the HTTP layer
(`test_admin_jobs_phase25.py`'s tests call `create_person_for_job(...)` directly and
never touch `response_model` serialization), so this would not be caught by the
current suite either way.

**Fix:** Verify empirically (a quick `httpx` round-trip against the real router), and
if it does raise, either drop `role_name` from `PersonResponse` (it's never
populated today) or inject it explicitly the same way `parse_stats`/`is_archived`/
`source` are injected elsewhere in this file, e.g. `person.__dict__["role_name"] = None`
before return, or switch the route to construct `PersonResponse(**{...})` from an
explicit dict instead of relying on ORM attribute traversal.

### WR-02: Dead `?incomplete=1` query param link on the pipeline job detail page

**File:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte:416`

**Issue:** The post-resolve provenance summary links to
`/admin/people?incomplete=1`:

```svelte
<a href="/admin/people?incomplete=1" ...>Review people →</a>
```

`app/src/routes/admin/people/+page.server.ts`'s `load()` only reads `tab`,
`missing`, and `tenure_gaps` from the URL (`incomplete` is not read at all), and
`api/services/admin_people.py::list_people` has no `incomplete` parameter either
(that filter mode was explicitly removed per the D-04/D-10 comments elsewhere in
this same file: "supersedes the removed `?incomplete=true` toggle"). Clicking this
link silently lands on the unfiltered Bench tab instead of any "needs attention"
view — it never filters anything.

**Fix:** Point this link at a working filter, e.g.
`/admin/people?tab=bench&missing=first%20name` is too narrow; more appropriately
drop the query string entirely (`/admin/people`) or route to the People dashboard's
incomplete-count card, whichever the intended UX for Phase 38's "Review people"
CTA is.

### WR-03: `AdminJobResponse`/`PersonResponse`-style attribute injection precedent suggests `create_person_for_job` may also be missing `role_name` when `role_id` is set via `role_name` lookup

**File:** `api/services/admin_jobs.py:928-951`

**Issue:** When `body.role_name` is supplied and a `Role` is found-or-created,
`role_id` is set on the new `Person`, but the created/found `Role.name` is never
attached back onto the `Person` instance for the `role_name` response field
(related to WR-01 above — even once the `AttributeError` risk is fixed by
injecting a default, the field would always serialize as `None` rather than the
operator-supplied role name, which is a silent information loss for any consumer
of this response relying on `role_name` to render immediately without a second
fetch).

**Fix:** After resolving `role_id`/`role`, set
`person.__dict__["role_name"] = role.name if role_id is not None else None` (or the
looked-up `Role.name`) before returning, consistent with the fix for WR-01.

## Info

### IN-01: `normalize_name_part` silently skips length validation for an unrecognized `field_name`

**File:** `api/domain/person_names.py:75-97`

**Issue:** `bound = _PART_BOUNDS.get(field_name)` returns `None` for any
`field_name` not in `{"first_name", "middle_name", "last_name", "name_suffix"}`, and
the subsequent `if bound is not None and len(collapsed) > bound` check is then
skipped entirely rather than raising. Every current call site passes a fixed
literal, so this is not reachable today, but it is a silent-degrade footgun for any
future caller that passes a typo'd or new field name — the function would appear
to validate but actually let an oversized value through unchecked.

**Fix:** Raise (e.g. `KeyError`/`AssertionError`) for an unrecognized `field_name`
instead of silently treating it as "no bound," or type `field_name` as a
`Literal[...]` so a bad call site fails at type-check time.

### IN-02: `PersonUpdate.tenures` accepts a list of arbitrary length with no dedupe/limit, and `_replace_tenures` fully deletes-then-reinserts on every save regardless of whether tenures actually changed

**File:** `api/services/admin_people.py:122-175`, `439-563`

**Issue:** Not a Phase 38 regression, but worth noting since `update_person` was
touched by this phase's merge logic: every `PATCH` that includes `tenures` (even an
unchanged list re-submitted by the client) deletes and reinserts every
`CourtTenure` row for the person, which discards the original row `id`s. This is
low risk functionally (the "id" field on `TenureWrite` is accepted but never used
by `_replace_tenures`), but it does mean any other table that might one day
reference `court_tenures.id` by FK would silently orphan on every unrelated name
edit that also carries the unchanged `tenures` array. No current FK depends on
`court_tenures.id` from another table today, so this is informational only.

**Fix:** No action required unless a future feature adds a dependent FK on
`court_tenures.id`; if so, `_replace_tenures` should diff rather than
delete-and-reinsert unconditionally.

---

_Reviewed: 2026-07-27T17:02:14Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
