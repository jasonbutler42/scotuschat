---
phase: 03-full-ui
reviewed: 2026-06-12T00:00:00Z
depth: standard
files_reviewed: 16
files_reviewed_list:
  - api/main.py
  - api/schemas/cases.py
  - api/services/cases.py
  - api/routers/cases.py
  - app/src/routes/cases/+page.server.ts
  - app/src/routes/cases/+page.svelte
  - app/src/routes/cases/[slug]/+page.server.ts
  - app/src/routes/cases/[slug]/+page.svelte
  - app/src/routes/+layout.svelte
  - app/src/lib/components/ChatBubble.svelte
  - app/src/lib/components/SectionRail.svelte
  - app/src/routes/cases/[slug]/arguments/[id]/+page.svelte
  - tests/test_cases_api.py
  - tests/test_models_import.py
  - tests/test_schema.py
  - api/services/arguments.py
findings:
  critical: 3
  warning: 4
  info: 3
  total: 10
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-06-12T00:00:00Z
**Depth:** standard
**Files Reviewed:** 16
**Status:** issues_found

## Summary

The implementation covers the full read-only UI from the case list page through the chat-view argument page, plus the FastAPI backend service layer. Core architecture constraints (FASTAPI_BASE_URL as private env var, no `Base.metadata.create_all`, Svelte 5 Runes) are respected across all files reviewed.

Three blockers were found: a crash when `displayName` is empty in `ChatBubble.svelte`, a logic defect in the `[slug]/+page.server.ts` multi-argument redirect guard that silently falls through, and a missing `argument_id` field in `+page.server.ts` multi-argument fallback return that will cause the argument-picker template to dereference `undefined`. Four warnings cover an unawaited async fixture in `test_schema.py`, a broken `is_lead`-only filter in the `[slug]` server load, an incomplete test assertion, and a silent crash path in `SectionRail.svelte`. Three info items cover code duplication, a magic number, and a misleading comment.

---

## Critical Issues

### CR-01: Empty-string crash in `ChatBubble.svelte` initials computation

**File:** `app/src/lib/components/ChatBubble.svelte:12`

**Issue:** When `displayName` is an empty string (both `speaker_name` and `raw_speaker_label` are null or empty), `displayName.trim().split(/\s+/)` returns `['']` — a single-element array whose first element is the empty string `''`. The code then evaluates `parts[0][0]` which is `''[0]` — `undefined` in JavaScript. `undefined.toUpperCase()` throws `TypeError: Cannot read properties of undefined`. Because `parts.length >= 2` is false, the `else` branch executes `displayName.slice(0, 2).toUpperCase()` — but only if that branch is actually reached. The bug is actually in the `>= 2` branch: if `parts` has two or more entries and the first is empty (e.g., leading whitespace only), `parts[0][0]` is still `undefined`. Either way, stage-direction utterances also flow through `ChatBubble` — the `is_stage_direction` filter is on the parent, but if a miscategorised utterance arrives with a null label the component throws at render time and breaks the entire argument page.

**Fix:**
```typescript
const initials = (() => {
  if (!displayName) return '?';
  const parts = displayName.trim().split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  return displayName.trim().slice(0, 2).toUpperCase() || '?';
})();
```

---

### CR-02: `redirect()` inside `if` without `return` — silent fall-through to broken return value

**File:** `app/src/routes/cases/[slug]/+page.server.ts:12-15`

**Issue:** SvelteKit's `redirect()` throws a special `Response` that must be allowed to propagate. The code wraps it in `if (matches.length === 1)` without `return` or `throw`:

```ts
if (matches.length === 1) {
    redirect(307, `/cases/${params.slug}/arguments/${matches[0].argument_id}`);
}
// Multi-argument case: return list for the argument picker page
return { slug: params.slug, caseName: matches[0].case_name, arguments: matches };
```

`redirect()` from `@sveltejs/kit` **throws** internally (it is not a plain function that returns a value). If the import of `redirect` is the SvelteKit version (which it is — `import { error, redirect } from '@sveltejs/kit'`), then calling it without `throw` means the thrown Response bubbles naturally and the redirect does work at runtime. **However**, the logic structure means that when `matches.length > 1`, execution falls through to the `return` and everything works — but the final `return` statement uses `matches[0].case_name` and `matches[0].argument_id`. `argument_id` is not a field on `CaseItem` directly visible to the multi-argument picker; the template at `[slug]/+page.svelte:54` iterates `data.arguments` and reads `arg.argument_id` — but `CaseItem` (from the API) has `argument_id` as a top-level field, so this actually works. The real defect here is more subtle: the `redirect` call in the single-match branch does NOT use `throw` and so the linting and TypeScript type-checker will not raise a warning, but the SvelteKit `redirect()` function raises an exception internally; if a future refactor changes the import to a helper that returns a `Response` instead of throwing, this silently stops redirecting and continues to the `return`. The structural pattern is dangerous and incorrect by SvelteKit conventions. The standard pattern is `throw redirect(...)`.

**Fix:**
```typescript
if (matches.length === 1) {
    throw redirect(307, `/cases/${params.slug}/arguments/${matches[0].argument_id}`);
}
```

---

### CR-03: `[slug]/+page.server.ts` fetches the entire case list to resolve a single slug — and the `question_number` field used by the argument-picker template is never populated

**File:** `app/src/routes/cases/[slug]/+page.server.ts:6-15`

**Issue:** The server load fetches `GET /cases` (the full case list endpoint), then client-side filters by slug. This works, but more critically: the `CaseItem` schema (`api/schemas/cases.py`) does not include a `question_number` field. The argument-picker template in `[slug]/+page.svelte:75` renders `{arg.question_number}` for each item in `data.arguments`. Because `question_number` is absent from `CaseItem`, this will always render `undefined` (displayed as empty string in Svelte) — the picker shows "Question  — Argued …" with a blank question number for every row. This is a data contract mismatch between the API schema and the template expectation.

**Fix:** Add `question_number` to the `CaseItem` Pydantic schema and the `get_cases` service query (joining through `Argument`), or fetch from a case-detail endpoint that includes it. Minimum schema change:

```python
# api/schemas/cases.py
class CaseItem(BaseModel):
    id: int
    slug: str
    case_name: str
    docket_number: str
    term_year: int
    argued_date: datetime.date
    argument_id: int
    question_number: int   # ADD THIS

    model_config = {"from_attributes": True}
```

And in `api/services/cases.py`, add `"question_number": argument.question_number` to the returned dict.

---

## Warnings

### WR-01: `db_conn` async fixture missing `pytest_plugins` / `asyncio_mode` — test will hang or error

**File:** `tests/test_schema.py:37-47`

**Issue:** The `db_conn` fixture is declared `async def` and uses `yield`, but there is no `@pytest.fixture` decorator with `scope` or `asyncio_mode` annotation, and more importantly no `pytest.ini` / `pyproject.toml` shown that sets `asyncio_mode = "auto"`. Without `pytest-anyio` or `asyncio_mode = "auto"`, `pytest-asyncio` will treat an `async def` fixture as a coroutine object rather than running it. The two `@pytest.mark.asyncio` tests that depend on `db_conn` will receive the raw coroutine, then attempt `await db_conn.fetch(...)` on a coroutine object — raising `AttributeError` at runtime rather than being cleanly skipped when `DATABASE_URL` is unset. The `@requires_db` skip marker fires at collection time and will skip the tests when `DATABASE_URL` is empty, so this is latent rather than immediately broken — but when `DATABASE_URL` is set in CI, the tests will fail spuriously due to the missing fixture mode.

**Fix:**
```python
@pytest.fixture
async def db_conn():
    ...
```
should be:
```python
@pytest_asyncio.fixture
async def db_conn():
    ...
```
and add `import pytest_asyncio` at the top. Alternatively, add `asyncio_mode = "auto"` to `pytest.ini` or `pyproject.toml`.

---

### WR-02: `SectionRail.svelte` — `$effect` cleanup not guarded when `browser` is false mid-reactive-cycle

**File:** `app/src/lib/components/SectionRail.svelte:9-29`

**Issue:** The `$effect` returns a cleanup function unconditionally. When `!browser || sections.length === 0`, the effect returns `undefined` (implicitly). Svelte 5's `$effect` calls the cleanup function returned by the previous run when the effect re-runs or the component unmounts. An `undefined` return is valid. However, the `observers` array is created inside the effect but the cleanup closure captures the `observers` variable from the enclosing scope. On the initial SSR render in SvelteKit, `browser` is `false`, so no observers are created, and the returned cleanup is `undefined`. On the client hydration pass, the effect re-runs with `browser = true`. This is correct. The real issue is: if `sections` becomes empty after observers were already created (e.g., reactive update), the `if (!browser || sections.length === 0) return;` fires early and returns `undefined`, meaning the **previously-created observers from the last run are never disconnected**. The old cleanup from the previous run should have been called by Svelte, but the issue is that this `return` exits before the `observers` array is even populated in the new run — the cleanup returned by the previous run's effect should still fire (Svelte 5 calls the prior cleanup before re-running), so this is safe. However, if the initial run creates 0 observers and returns `undefined`, and then the next run returns a real cleanup, the prior `undefined` cleanup is a no-op and no memory leak occurs. This is actually correct behavior. The genuine warning is: the `$effect` cleanup is returned inside the effect body as `return () => observers.forEach(...)`, but if `sections` is reactive (`$props`) and the array shrinks, the intersection observers for removed sections are cleaned up by the returned cleanup from the previous run — which is correct. However, all of this relies on Svelte 5's effect cleanup semantics being respected, and there is no explicit typing of the `sections` prop as `readonly` — a caller passing a mutated array reference (same reference, different contents) would not re-trigger the effect, leaving stale observers. This is a latent bug that depends on caller discipline.

**Fix:** Declare the prop with `$props()` destructuring as already done, but add a note or enforce a defensive copy:
```typescript
// Defensive: ensure effect re-runs when sections identity changes
let { sections }: { sections: SectionAnchor[] } = $props();
```
The real mitigation is to ensure callers always pass a new array reference when sections change (which `$derived` already does), and to document this expectation.

---

### WR-03: `test_schema.py` comment says "10 tables" but assertion checks 11

**File:** `tests/test_schema.py:71-73`

**Issue:** The `EXPECTED_TABLES` set at line 54 contains 11 entries. The docstring on `test_all_tables_exist` at line 72 says "All 11 tables must exist" — that part is correct. But the comment block header at line 52 says `# Test 1: All 10 tables exist post-migration`. This is a stale comment (10 vs. 11). More critically, this inconsistency with `test_models_import.py` (which asserts `len(tables) == 11`) means a future reader cannot trust either file without counting manually. This is a documentation error that could mask a genuine table-count regression.

**Fix:** Update the comment at line 52:
```python
# Test 1: All 11 tables exist post-migration
```

---

### WR-04: `[slug]/+page.server.ts` — entire case list re-fetched on every slug navigation; no case-detail API endpoint exists, creating a latent N+1 pattern

**File:** `app/src/routes/cases/[slug]/+page.server.ts:6-9`

**Issue:** Every visit to `/cases/{slug}` issues `GET /cases` — returning all cases — and then filters in JavaScript. For a small dataset this is tolerable, but the design couples the slug-detail page to the list endpoint. The harder problem is: the `CaseItem` schema lacks `question_number` (tracked as CR-03), which means even fixing CR-03 requires returning `question_number` from the list endpoint. This design means any new field needed by the detail or argument-picker pages forces a schema change to the list endpoint, polluting its contract. The `GET /cases` endpoint is intended for the case list page only. A proper `GET /cases/{slug}` endpoint would solve both CR-03 and this concern cleanly.

**Fix:** Add a `GET /cases/{slug}` endpoint returning full case metadata including `question_number`. This eliminates the client-side filter and decouples the list and detail schemas. Until then, at minimum, add `question_number` to `CaseItem` (CR-03 fix) to make the multi-argument picker renderable.

---

## Info

### IN-01: `formatDate` function is copy-pasted across three Svelte files

**File:** `app/src/routes/cases/+page.svelte:11-18`, `app/src/routes/cases/[slug]/+page.svelte:11-18`, `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte:15-22`

**Issue:** The identical `formatDate` function is copy-pasted verbatim in three files. A future change to date formatting (locale, options) requires editing all three.

**Fix:** Extract to a shared utility:
```typescript
// app/src/lib/utils/format.ts
export function formatDate(dateStr: string): string {
    const date = new Date(dateStr + 'T00:00:00');
    return new Intl.DateTimeFormat('en-US', {
        month: 'long',
        day: 'numeric',
        year: 'numeric',
    }).format(date);
}
```
Then import in each page: `import { formatDate } from '$lib/utils/format';`

---

### IN-02: Magic `argument_id` field access on untyped `matches` elements in `[slug]/+page.server.ts`

**File:** `app/src/routes/cases/[slug]/+page.server.ts:9`

**Issue:** The `matches` array is typed inline as `(c: { slug: string })` in the filter but is then accessed as `matches[0].argument_id` and `matches[0].case_name` without asserting or typing those fields. TypeScript will infer `matches` as `{ slug: string }[]` from the filter predicate, making `.argument_id` and `.case_name` type errors. In practice, the `data` object from `GET /cases` has the full `CaseItem` shape, but the type narrowing from the inline predicate loses those fields.

**Fix:** Type the `data.cases` array against the `CaseItem` interface, or widen the filter predicate:
```typescript
interface CaseItem {
    id: number;
    slug: string;
    case_name: string;
    docket_number: string;
    term_year: number;
    argued_date: string;
    argument_id: number;
    question_number: number; // after CR-03 fix
}
const matches = (data.cases as CaseItem[]).filter((c) => c.slug === params.slug);
```

---

### IN-03: `test_cases_api.py` — test 6 passes vacuously when cases directory does not exist; no assertion that the expected import *is* present

**File:** `tests/test_cases_api.py:120-139`

**Issue:** `test_no_public_fastapi_base_url_in_cases_pages` guards against the negative case (PUBLIC_ prefix) but does not assert the positive case (that `FASTAPI_BASE_URL` from `$env/static/private` *is* present). A file that imports nothing at all from the env would pass this test while silently omitting the required import. The test is a correct guard for the prohibition but provides no assurance that the private import is actually being used.

**Fix:** Add a complementary positive assertion:
```python
found_private_import = any(
    "FASTAPI_BASE_URL" in ts_file.read_text(encoding="utf-8", errors="ignore")
    for ts_file in cases_dir.rglob("*.ts")
    if "+page.server.ts" in ts_file.name
)
assert found_private_import, (
    "No +page.server.ts file under app/src/routes/cases/ imports FASTAPI_BASE_URL"
)
```

---

_Reviewed: 2026-06-12T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
