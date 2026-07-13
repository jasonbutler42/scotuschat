---
phase: 32-fix-courttenure-fk-bookkeeping-gap-in-merge-delete-person-se
reviewed: 2026-07-13T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - api/schemas/admin_people.py
  - api/services/admin_people.py
  - api/tests/test_admin_people_merge.py
  - app/src/routes/admin/people/[id]/+page.server.ts
  - app/src/routes/admin/people/[id]/+page.svelte
findings:
  critical: 0
  warning: 5
  info: 1
  total: 6
status: issues_found
---

# Phase 32: Code Review Report

**Reviewed:** 2026-07-13T00:00:00Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Phase 32's actual code change (confirmed via `git show 3f9d2059`, `73f721d9`, `67336a4f`, `6e25fe04`) is narrow and well-executed: `CourtTenure` was added as the 5th FK table to `MergePreview`, `get_merge_preview`, `merge_people`, and `delete_person_if_orphan`, with matching frontend (`+page.server.ts` blocking-tier computation, `+page.svelte` preview display) and test coverage. I traced every touched code path (schema field, service loop, atomicity/commit ordering, transaction guards, and the mirrored test suite) and found no correctness defect in the CourtTenure bookkeeping itself — counts, transfers, and blocking behavior are internally consistent across all five files.

However, reviewing the full files (as scoped) surfaced pre-existing and adjacent issues that either regress with this change's pattern or were never caught: a documented CLAUDE.md invariant (`statement_cache_size=0` for PgBouncer) is violated by every DB-gated test in the file, including the three new ones; two of the new tests can leak un-cleaned rows into the shared database on assertion failure; the aliases-are-excluded-from-blocking design (intentional, per commit message) has no in-code comment explaining why, inviting a future regression exactly like the one this phase just fixed for tenures; and the frontend's `PersonListItem` type/rendering path references `last_name`/`first_name` fields the backend never sends, so a "Last, First" merge-picker sort silently never activates.

No Critical/security issues found.

## Warnings

### WR-01: DB-gated tests bypass the project's mandatory `statement_cache_size=0` PgBouncer setting

**File:** `api/tests/test_admin_people_merge.py:107,127,173,192,227,246,303,352,402`

**Issue:** Every DB-gated test in this file (including the three new Phase 32 tests — `test_get_merge_preview_counts_tenures` at line 303, `test_delete_person_if_orphan_blocked_by_tenure` at line 352, `test_merge_people_transfers_tenures` at line 402) creates its own ad-hoc engine:

```python
engine = create_async_engine(os.environ["DATABASE_URL"], echo=False)
```

`api/core/database.py` documents this as a hard invariant: `statement_cache_size=0` **must** be passed via `connect_args` for asyncpg behind Digital Ocean's PgBouncer in Transaction mode (CLAUDE.md: *"asyncpg requires `statement_cache_size=0` when behind Digital Ocean PgBouncer (Transaction mode). This must be in the initial engine config."*). None of these test engines set it. If `DATABASE_URL` in CI/staging ever points through PgBouncer (the documented production topology), these tests will intermittently fail with asyncpg prepared-statement errors that have nothing to do with the logic under test.

**Fix:** Extract a shared test helper (e.g. in `conftest.py`) that mirrors the production engine config:

```python
def make_test_engine():
    return create_async_engine(
        os.environ["DATABASE_URL"],
        echo=False,
        connect_args={"statement_cache_size": 0},
    )
```

and use it in place of every inline `create_async_engine(os.environ["DATABASE_URL"], echo=False)` call in this file.

### WR-02: New CourtTenure tests leak rows on assertion failure and use non-deterministic lookups

**File:** `api/tests/test_admin_people_merge.py:340-387` (`test_delete_person_if_orphan_blocked_by_tenure`), `390-448` (`test_merge_people_transfers_tenures`)

**Issue:** Unlike `test_get_merge_preview_counts_tenures` (which wraps its work in a single `async with db.begin():` block that auto-rolls-back on exception), these two new tests use several sequential `async with async_session() as db:` blocks with explicit `await db.commit()` calls. If any `assert` in the test body fails (e.g. `assert result is False` at line 374), the cleanup code at the bottom of the test (lines 382-385 / 443-446) never runs, and the already-committed `Person`/`CourtTenure` rows leak permanently into the shared database. A subsequent run of the suite then does `SELECT id FROM people WHERE full_name = '...' LIMIT 1` with no `ORDER BY` (line 361, 411-414), which is non-deterministic once duplicates exist (`full_name` has no unique constraint on `Person`) — a rerun could silently grab a stale leaked row instead of the fresh one just inserted, producing confusing false passes/failures.

**Fix:** Wrap each test's setup + assertions + cleanup in a single `async with db.begin():` block (as `test_get_merge_preview_counts_tenures` already does) so a failed assertion rolls back automatically instead of leaking rows.

### WR-03: Aliases-excluded-from-blocking design is undocumented at the point of use

**File:** `app/src/routes/admin/people/[id]/+page.server.ts:94-115`

**Issue:** `can_delete` and `delete_block_count` deliberately omit `counts.aliases` (per the Phase 32 commit message: *"aliases remains excluded from both (auto-delete tier, unchanged)"*), while every other count (`utterances`, `appearances`, `argument_participants`, and now `tenures`) is included. The comment above this block only says *"counts reflect source FKs only, D-09"* — it does not explain why `aliases` is the one field left out. This is exactly the kind of omission that just got "fixed" for `tenures` in this same phase; without an explicit comment, a future change extending this list (e.g., for a new FK table) is one accidental edit away from also including `aliases` and reintroducing the Phase-12 Gap-B regression (aliases blocking an otherwise-orphan delete).

**Fix:** Add a comment directly above the `can_delete` assignment, e.g.:

```ts
// aliases is intentionally excluded here — SpeakerAlias rows are name
// variants intrinsic to the person and are auto-deleted by
// delete_person_if_orphan regardless of orphan status (Phase 12 Gap B).
// Do not add counts.aliases to this list.
can_delete =
    counts.utterances === 0 &&
    counts.appearances === 0 &&
    counts.argument_participants === 0 &&
    counts.tenures === 0;
```

### WR-04: `PersonListItem` frontend type references fields the backend never returns

**File:** `app/src/routes/admin/people/[id]/+page.server.ts:39-44`, `app/src/routes/admin/people/[id]/+page.svelte:725`, `745`, `768`

**Issue:** The frontend `PersonListItem` interface declares `last_name: string | null` and `first_name: string | null`:

```ts
interface PersonListItem {
	id: number;
	full_name: string;
	last_name: string | null;
	first_name: string | null;
}
```

but the backend `PersonListItem` schema (`api/schemas/admin_people.py:47-71`) has no `last_name`/`first_name` fields, and `list_people()`'s row dict (`api/services/admin_people.py:306-321`) never computes them either. `GET /api/admin/people` (which feeds `data.people`) can therefore never return these keys. The merge-target `<select>` in `+page.svelte` relies on this to format "Last, First":

```svelte
{p.last_name ? `${p.last_name}, ${p.first_name ?? ''}` : p.full_name}
```

Since `p.last_name` is always `undefined`, this condition is always falsy and the code silently always falls back to `p.full_name` — the "Last, First" formatting never activates. Not a crash (falls back safely), but it is dead code masquerading as working functionality, and the type annotations actively lie about the API contract at this boundary.

**Fix:** Either (a) extend the backend `PersonListItem` schema and `list_people()` to include `first_name`/`last_name` so the intended formatting works, or (b) remove the dead fields from the frontend `PersonListItem` interface and the `last_name`-based formatting branches in `+page.svelte` (lines 725, 745, 768) if "Last, First" display was never actually required.

### WR-05: `delete_person_if_orphan`'s unconditional alias delete has no explicit rollback guarantee

**File:** `api/services/admin_people.py:650-667`

**Issue:**

```python
# Delete name-variant aliases first — they are intrinsic to the person (Gap B fix).
await db.execute(
    delete(SpeakerAlias)
    .where(SpeakerAlias.person_id == person_id)
    .execution_options(synchronize_session=False)
)

for model, col in [
    (Utterance, Utterance.person_id),
    (CaseAppearance, CaseAppearance.person_id),
    (ArgumentParticipant, ArgumentParticipant.person_id),
    (CourtTenure, CourtTenure.person_id),
]:
    count = ...
    if count > 0:
        return False  # Not orphaned — caller returns 409 (D-06)
```

`SpeakerAlias` rows are deleted unconditionally, before the orphan check across the other four tables runs. If the person is blocked (e.g. has a `CourtTenure` row), the function returns `False` without ever calling `db.commit()`. Today this is safe only because `api/core/database.py`'s `get_db()` dependency uses a plain `async with AsyncSessionLocal() as session: yield session` with no implicit commit-on-exit, so the uncommitted `SpeakerAlias` delete is rolled back when the session closes. That safety is an unstated invariant of the *caller's* session lifecycle, not something this function enforces itself — any future change to `get_db()` (or a different caller that commits unconditionally) would silently and permanently strip a blocked person's aliases while leaving the person record intact and un-deleted.

**Fix:** Make the guarantee explicit rather than relying on caller-side session semantics — either move the `SpeakerAlias` delete to after the orphan-check loop passes (only run it right before the final `Person` delete + commit), or add an explicit `await db.rollback()` on the early-return path:

```python
for model, col in [...]:
    count = ...
    if count > 0:
        await db.rollback()  # undo the alias delete above; person is not orphaned
        return False
```

## Info

### IN-01: Docstring overstates the orphan-check coverage

**File:** `api/services/admin_people.py:636-644`

**Issue:** The docstring says *"COUNT check covers all 5 FK tables"*, but only 4 tables (`Utterance`, `CaseAppearance`, `ArgumentParticipant`, `CourtTenure`) go through a `COUNT` check in the loop — `SpeakerAlias` (the 5th table) is unconditionally deleted, not counted. The surrounding prose (*"Delete a person only if they have zero rows across all 5 FK tables"*) is accurate in effect since aliases never block, but the specific "COUNT check ... 5 FK tables" sentence is not literally true.

**Fix:** Reword to something like: *"COUNT check covers 4 FK tables; SpeakerAlias rows are deleted unconditionally above and never block (Gap B, Phase 12)."*

---

_Reviewed: 2026-07-13T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
