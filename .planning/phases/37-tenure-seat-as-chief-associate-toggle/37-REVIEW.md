---
phase: 37-tenure-seat-as-chief-associate-toggle
reviewed: 2026-07-21T22:40:11Z
depth: standard
files_reviewed: 24
files_reviewed_list:
  - alembic/versions/0020_rename_tenure_seat_to_office.py
  - alembic/versions/0021_constrain_tenure_office.py
  - api/models/models.py
  - api/schemas/admin_people.py
  - api/schemas/speakers.py
  - api/services/admin_people.py
  - api/services/speakers.py
  - api/tests/test_admin_arguments_service.py
  - api/tests/test_admin_dashboard_stats.py
  - api/tests/test_admin_people_merge.py
  - api/tests/test_admin_people_phase25.py
  - api/tests/test_admin_people_schemas_service.py
  - api/tests/test_speakers_service.py
  - app/src/lib/components/SpeakerPopover.svelte
  - app/src/routes/admin/people/[id]/+page.server.ts
  - app/src/routes/admin/people/[id]/+page.svelte
  - app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts
  - app/src/routes/cases/[slug]/arguments/[id]/+page.svelte
  - app/tests/tenure-office.browser.test.mjs
  - app/tests/tenure-public-title.browser.test.mjs
  - pipeline/commands/import_justices_csv.py
  - pipeline/tests/test_import_justices_csv.py
  - scripts/audit_tenure_seat_identifiers.py
  - scripts/migrate_tenure_offices.py
  - tests/test_migrate_tenure_offices.py
findings:
  critical: 1
  warning: 4
  info: 3
  total: 8
status: issues_found
---

# Phase 37: Code Review Report

**Reviewed:** 2026-07-21T22:40:11Z
**Depth:** standard
**Files Reviewed:** 24
**Status:** issues_found

## Summary

Phase 37 renames `CourtTenure.seat` (free text) to a canonical two-value
`office` (`chief`/`associate`) across a staged Alembic migration
(0020 rename-only → `scripts/migrate_tenure_offices.py` data normalization →
0021 CHECK + NOT NULL), the ORM/API/service layers, the justices CSV
importer, read-side formal-title projection, and the admin People editor.

The migration-safety design is solid: the rename step (0020) makes no data
changes, `migrate_tenure_offices.py` uses a signed/hashed dry-run report,
row-level `FOR UPDATE` locks, a whole-table drift check before the first
`UPDATE`, and a single transaction with a postcondition re-check before
commit; the constrain step (0021) preflights for any unresolved/NULL row
before adding the CHECK constraint and flipping NOT NULL, and fails loudly
if any exist. All discovered `CourtTenure`-row-creating call sites (the
admin People editor's `_replace_tenures`, and the justices CSV importer)
always supply a canonical `office`, so the NOT NULL constraint is never at
risk of being violated by application code. The admin editor's "atomic
save" claim also holds up: `update_person` never calls `db.commit()` until
every field (including tenure replacement) has succeeded, and a raised
`ValueError` (malformed date, invalid office pre-Pydantic edge cases) is
caught by the router and turned into a 422 with no explicit rollback — but
that's safe here, because the FastAPI `get_db` dependency's
`async with AsyncSessionLocal() as session` block implicitly rolls back any
uncommitted work when the exception propagates out of the endpoint, so a
failed save leaves no partial tenure rows.

The one correctness gap that stood out is that `office_title()` (the
formal-title projection helper) is unconditionally called with a
DB-sourced `office` value in three places and raises a bare `KeyError` for
anything outside `{"chief", "associate"}` — which is exactly the state
`court_tenures.office` is allowed to be in during the phase's own
documented rollout window (after 0020's rename, before the operator runs
`migrate_tenure_offices.py --execute` and applies 0021). See CR-01.

Remaining issues are lower-severity: a missing `ORDER BY` on one tenure
prefetch that could make bench-role resolution nondeterministic for
overlapping tenure windows, a client-side dead-end where an invalid tenure
row can become unreachable if the operator switches to Advocate, a
pre-existing `is_bench` derivation that can misclassify a tenure-less
Justice as an Advocate for popover styling, and a couple of small
maintainability/code-quality notes.

## Critical Issues

### CR-01: `office_title()` raises an unhandled `KeyError` for any non-canonical office value, and all three call sites invoke it unguarded

**File:** `api/models/models.py:151-159`, `api/services/admin_people.py:828`, `api/services/speakers.py:77` and `:86`

**Issue:** `office_title()` is documented as "exhaustive over `VALID_OFFICES` — raises `KeyError` for any other input," and every call site (`admin_people._bench_role_and_missing_tenure`, reused by `admin_arguments.list_argument_speakers`; `speakers._tenure_role_name`, used by the public speaker-popover endpoint) calls it with a DB-sourced `CourtTenure.office` value and no `try/except`. That's fine *after* migration 0021 has applied its CHECK + NOT NULL constraint — but this phase's own rollout plan has a real, documented window where it is not yet true: migration 0020 renames `seat` → `office` while leaving the column **nullable and unconstrained**, and only after an operator runs `scripts/migrate_tenure_offices.py --execute` (a separate, manual step) does migration 0021 add the CHECK/NOT NULL. If the FastAPI app keeps serving traffic during that window (a normal expectation for an App Platform deploy, and nothing in this phase adds a maintenance-mode gate), any bench participant whose tenure still holds a legacy value (e.g. `"Associate Justice Seat 3"`) and covers the argument's `argued_date` will make `office_title()` raise, producing an unhandled 500 for:
- `GET /api/admin/jobs/{id}/resolve-rows` (the pipeline Resolve card)
- the admin argument editor's Speakers section (`admin_arguments.list_argument_speakers`)
- the public `GET /arguments/{id}/speakers` endpoint that the public argument page depends on (fails open only because the SvelteKit loader catches non-OK responses and renders `[]`, but the admin-side callers have no such guard)

The client-side mirror of this same mapping (`SpeakerPopover.svelte`'s `officeTitle()`) was written defensively (`OFFICE_TITLES[office] ?? ''`), which only underscores that the server-side helper's "never silently coerce" contract is safe for validated data but unsafe as the sole gate against a state the phase's own migration plan permits to exist transiently.

**Fix:** Make the interim window non-fatal, e.g.:
```python
def office_title(office: str) -> str | None:
    """Return the formal display title, or None if office is not (yet) canonical."""
    return OFFICE_TITLES.get(office)
```
and have callers treat a `None` result the same as `missing_tenure=True` (or equivalent "not yet resolvable" state), instead of asserting the DB has already reached its final constrained shape. Alternatively, wrap each of the three call sites in `try/except KeyError` and degrade to the existing "missing tenure" / null-role path.

## Warnings

### WR-01: Bench tenure prefetch in `list_resolve_rows_for_job` has no deterministic ordering

**File:** `api/services/admin_people.py:900-905`

**Issue:** The tenure prefetch that feeds `_bench_role_and_missing_tenure` for the Resolve card is:
```python
tenures_result = await db.execute(
    select(CourtTenure).where(CourtTenure.person_id.in_(bench_person_ids))
)
```
with no `ORDER BY`. `_bench_role_and_missing_tenure` returns the *first* tenure in list order whose window covers `argued_date`, so if a person ever has two windows that both technically cover a given date (e.g. a transition day where an old tenure's `end_date` equals a new tenure's `start_date`), which office title gets shown depends on unspecified Postgres row order. The sibling implementation for the exact same lookup, `speakers.get_argument_speakers`, already guards against this with `.order_by(CourtTenure.person_id.asc(), CourtTenure.start_date.asc())` — so the public popover and the admin Resolve card can disagree for the same person/date.

**Fix:**
```python
tenures_result = await db.execute(
    select(CourtTenure)
    .where(CourtTenure.person_id.in_(bench_person_ids))
    .order_by(CourtTenure.start_date.asc())
)
```

### WR-02: Save can become permanently blocked by an invalid tenure row that's unreachable once "Advocate" is selected

**File:** `app/src/routes/admin/people/[id]/+page.svelte:138-164`, `:584-837`

**Issue:** `handleSaveClick`'s client-side preflight (`firstInvalidOfficeIndex`) blocks the *entire* Save Person submission whenever any row in `tenureRows` has `office === null`, regardless of the current Bench/Advocate toggle. But the only markup that lets an operator fix or remove such a row (the "Tenure Periods" section, including the `Remove` button) is rendered only `{#if isJustice}`. If an operator switches Person Type to Advocate while a legacy-invalid tenure row is still present in local state (e.g. loaded from a person who had a not-yet-migrated tenure, or restored via the `form?.tenures` failed-save rehydration effect), Save Person becomes unclickable with the "Select Chief or Associate for every tenure period before saving." error, and there is no way to reach the offending row's Remove button to clear it while Advocate is selected — the operator's only escape is to toggle back to Bench.

**Fix:** Either gate the client-side blocking check on `isJustice` (mirroring the fact the server only requires resolvable tenures conceptually tied to Bench people), or keep the tenure list (or at least invalid rows) visible/removable regardless of the Bench/Advocate toggle.

### WR-03: `is_bench` is derived from tenure-row count, not from `side`, and can misclassify a Justice with zero tenures

**File:** `app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts:36`

**Issue:** `const is_bench = (s.tenure?.length ?? 0) > 0;` determines whether `SpeakerPopover.svelte` renders the Bench-only block (formal office title, tenure date range, appointing president) — but the same `SpeakerPopoverEntry` payload already carries an authoritative `side` field ("raw SideEnum value for isBench rendering logic", per its own doc comment). A Justice whose `ArgumentParticipant.side == BENCH` but who has zero `CourtTenure` rows (a real, reachable data state — e.g. `list_people`'s own "no tenures" missing-field flag exists precisely because this happens) will have `is_bench` computed `false` here, so the popover silently renders them with Advocate styling (blue avatar, no title/tenure block) instead of a Bench-with-missing-tenure treatment. This predates Phase 37 but sits directly upstream of the office-title rendering path this phase added, so it directly affects whether `officeTitle()` is ever invoked for that speaker.

**Fix:** Derive `is_bench` from `s.side === 'BENCH'` (already present on the payload) rather than tenure-array length.

### WR-04: Formal office-title mapping is duplicated (Python + Svelte) with no shared source of truth

**File:** `api/models/models.py:145-159`, `app/src/lib/components/SpeakerPopover.svelte:14-21`

**Issue:** `OFFICE_TITLES = {"chief": "Chief Justice", "associate": "Associate Justice"}` is defined independently in the backend (`models.py`) and the frontend (`SpeakerPopover.svelte`), tied together only by comments ("mirrors api/models/models.py's OFFICE_TITLES... D-15"). Nothing enforces the two stay in sync; a future change to either canonical values or their display titles requires remembering to update both files by hand.

**Fix:** Not urgent given only two fixed values exist today, but worth a follow-up note (e.g. generate the frontend constant from the backend one, or add a cross-file assertion in a shared test) if office values are ever extended.

## Info

### IN-01: `_db_configured()`'s `"sk-ant" not in url` check is a copy-paste artifact that doesn't validate a DATABASE_URL

**File:** `scripts/migrate_tenure_offices.py:29-30` (and the same helper duplicated in `api/tests/test_admin_people_merge.py:27`, `api/tests/test_admin_people_phase25.py:34`, `api/tests/test_admin_people_schemas_service.py:453`)

**Issue:** `_db_configured` checks `"sk-ant" not in url` — a substring check that looks like it was copied from an unrelated guard against an Anthropic API key being pasted into a DB-URL env var. It doesn't validate anything about a Postgres connection string's shape and reads oddly in a script whose whole purpose is a careful, audited DB migration. Low practical impact (the adjacent placeholder-URL check does the real work), but worth cleaning up so a future reader doesn't have to guess why an LLM API key prefix is being checked here.

### IN-02: `write_report()` is check-then-write, not atomic — an interrupted run can leave an unusable report file

**File:** `scripts/migrate_tenure_offices.py:74-78`

**Issue:**
```python
def write_report(path: Path, report: dict) -> None:
    path = Path(path)
    if path.exists():
        raise FileExistsError(...)
    path.write_text(...)
```
If the process is interrupted between the existence check and the write completing (or mid-write), the report file is left partially written. A re-run then hits `FileExistsError` pointing at a corrupt file, requiring the operator to manually delete it before retrying. Given this is a manually-run, offline, one-shot operator tool, severity is low, but writing to a temp file and `os.replace()`-ing it into place would close the gap.

### IN-03: `_replace_tenures`'s per-row office re-validation loop is currently unreachable

**File:** `api/services/admin_people.py:148-152`

**Issue:** The loop `for t in tenures: if t.office not in VALID_OFFICES: raise ValueError(...)` is documented as intentional defense-in-depth, but its only caller passes `tenures: list[TenureWrite]`, and `TenureWrite.office` is already a strict Pydantic `Literal["chief", "associate"]` — meaning every `TenureWrite` instance that can exist has already had this exact invariant enforced before `_replace_tenures` is ever called. As written, this branch cannot fire from any real code path today. Not asking for removal (the comment's rationale — a second belt-and-suspenders check before an irreversible delete — is reasonable), just flagging that it is presently dead in practice, in case that surprises a future reader trying to hit it with a test.

---

_Reviewed: 2026-07-21T22:40:11Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
