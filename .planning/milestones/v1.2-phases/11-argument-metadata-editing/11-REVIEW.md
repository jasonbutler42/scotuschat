---
phase: 11-argument-metadata-editing
reviewed: 2026-06-22T00:00:00Z
depth: standard
files_reviewed: 16
files_reviewed_list:
  - alembic/versions/0007_add_published_at.py
  - api/tests/test_published_gate.py
  - api/models/models.py
  - api/services/cases.py
  - api/schemas/admin_arguments.py
  - api/services/admin_arguments.py
  - api/tests/test_admin_arguments_service.py
  - api/tests/test_admin_arguments_routes.py
  - api/routers/admin.py
  - app/src/routes/admin/arguments/+page.server.ts
  - app/src/routes/admin/arguments/+page.svelte
  - app/src/routes/admin/arguments/[id]/+page.server.ts
  - app/src/routes/admin/arguments/[id]/+page.svelte
  - app/src/lib/components/TopNav.svelte
  - app/src/routes/admin/pipeline/[job_id]/+page.server.ts
  - app/src/routes/admin/pipeline/[job_id]/+page.svelte
findings:
  critical: 1
  warning: 4
  info: 3
  total: 8
status: issues_found
---

# Phase 11: Code Review Report

**Reviewed:** 2026-06-22
**Depth:** standard
**Files Reviewed:** 16
**Status:** issues_found

## Summary

Phase 11 adds argument metadata editing (case title, docket number, argued date), publish/unpublish workflow, and a pipeline job page argument preview. The backend implementation is solid: the mass-assignment guard on `ArgumentUpdate`, the publish gate enforcing `resolved_at IS NOT NULL`, and the SQLAlchemy ORM mutation pattern in `update_argument` are all correct. The migration is clean. The tests cover the security-critical paths (T-11-MASS, T-11-PUBGATE, T-11-IDOR, T-11-AC).

Two issues require attention before this ships. The pipeline job load function (`+page.server.ts`) uses the global `fetch` instead of SvelteKit's event-scoped `fetch` — a BLOCKER because it bypasses SvelteKit's server-side fetch instrumentation and breaks the architecture rule that all server-side FastAPI calls go through the event `fetch`. The admin argument list publish/unpublish actions silently discard API errors, leaving the operator with no feedback when a publish attempt fails for a legitimate reason.

---

## Critical Issues

### CR-01: Pipeline job `load` uses global `fetch` instead of SvelteKit event `fetch`

**File:** `app/src/routes/admin/pipeline/[job_id]/+page.server.ts:20`

**Issue:** The `load` function destructures only `{ params }` from the SvelteKit load event. All four internal `fetch()` calls — job, people, participants, and argument — use the Node.js global `fetch` rather than the event-scoped SvelteKit `fetch`. The CLAUDE.md architecture rule states: "All FastAPI calls from SvelteKit go through `+page.server.ts` server load functions — `FASTAPI_BASE_URL` is a server-only env var, never `PUBLIC_`." The event-scoped `fetch` is what enforces this: it is server-only, properly instrumented for SvelteKit's SSR lifecycle, and is how the framework guarantees request-context propagation. Every other `load` function in this phase (arguments list, arguments detail) correctly destructures `fetch` from the event. This file does not.

**Fix:**
```typescript
// Change line 20:
export const load: PageServerLoad = async ({ params }) => {

// To:
export const load: PageServerLoad = async ({ params, fetch }) => {
```
No other changes required — the four `fetch(...)` calls inside the function body will automatically resolve to the event-scoped `fetch` once it is in scope.

---

## Warnings

### WR-01: Publish/unpublish list-page actions discard API errors silently

**File:** `app/src/routes/admin/arguments/+page.server.ts:42–75`

**Issue:** Both `publish` and `unpublish` actions catch network errors but never check `res.ok` on the FastAPI response. The handler makes the fetch call, ignores any non-2xx status, and unconditionally throws `redirect(303, '/admin/arguments')`. If the API returns 422 ("Cannot publish: resolve step not yet complete" or "Already published"), the operator is silently redirected to the list with no indication that the action failed. The backend guard (T-11-PUBGATE) is correct, but the frontend discards its error signal entirely.

**Fix:** Check `res.ok` and return a `fail()` response when the API rejects the action, instead of unconditionally redirecting:
```typescript
publish: async ({ request, fetch }) => {
    const formData = await request.formData();
    const argument_id = formData.get('argument_id') as string;

    let res: Response;
    try {
        res = await fetch(`${FASTAPI_BASE_URL}/api/admin/arguments/${argument_id}/publish`, {
            method: 'POST',
            headers: { 'X-Admin-Token': ADMIN_TOKEN },
        });
    } catch (err) {
        console.error('[arguments publish] fetch threw:', err instanceof Error ? err.message : String(err));
        return fail(502, { error: 'Could not publish this argument. Try again.' });
    }

    if (!res.ok) {
        return fail(422, { error: 'Could not publish this argument. Try again.' });
    }

    throw redirect(303, '/admin/arguments');
},
```
Apply the same pattern to the `unpublish` action.

---

### WR-02: `update_argument` does not reject empty strings for `case_name` and `docket_number`

**File:** `api/services/admin_arguments.py:179–200`

**Issue:** `body.docket_number.strip()` and `body.case_name.strip()` are called but their result is never checked for emptiness before being written to the database. A PATCH body of `{"case_name": "   "}` would strip to `""` and persist an empty string as the lead case name, which would generate a slug of `""` from `_derive_slug` and corrupt the URL routing. The `ArgumentUpdate` schema has no `min_length` constraint on these fields.

**Fix:** Add emptiness guards after stripping, mirroring the date validation pattern:
```python
if body.docket_number is not None:
    new_docket = body.docket_number.strip()
    if not new_docket:
        raise ValueError("docket_number cannot be empty")
    # ... existing collision check ...

if body.case_name is not None:
    stripped_name = body.case_name.strip()
    if not stripped_name:
        raise ValueError("case_name cannot be empty")
    lead_case.case_name = stripped_name
    # ... existing slug logic ...
```
Alternatively add `min_length=1` to both fields in `ArgumentUpdate` via Pydantic `Field(min_length=1)` so the guard sits at the schema layer before the service is called.

---

### WR-03: `argument_id` from form data is used raw in a URL without integer validation

**File:** `app/src/routes/admin/arguments/+page.server.ts:44,47,63,66`

**Issue:** `argument_id = formData.get('argument_id') as string` is interpolated directly into the fetch URL without integer parsing or format validation. The value comes from a hidden form field which an operator could manipulate. A value like `"1/../../other-path"` would construct `FASTAPI_BASE_URL/api/admin/arguments/1/../../other-path/publish`. This is an admin-only endpoint behind token auth, so exploitation requires a compromised operator session, but the unvalidated interpolation still violates the input validation principle and could cause unexpected requests to unintended FastAPI routes.

**Fix:** Parse and validate `argument_id` as an integer before use:
```typescript
const argument_id_raw = formData.get('argument_id') as string;
const argument_id = parseInt(argument_id_raw, 10);
if (isNaN(argument_id) || argument_id <= 0) {
    return fail(400, { error: 'Invalid argument ID.' });
}
// then use argument_id (the number) in the URL template literal
await fetch(`${FASTAPI_BASE_URL}/api/admin/arguments/${argument_id}/publish`, ...);
```
Apply the same fix to the `unpublish` action.

---

### WR-04: `test_get_cases_preserves_return_keys` searches the whole file, not the function body

**File:** `api/tests/test_published_gate.py:101–118`

**Issue:** The other three tests in `TestPublishedGate` correctly extract `get_cases()` source lines using the AST before asserting on them. `test_get_cases_preserves_return_keys` reads the entire `cases.py` source and checks for string key literals file-wide. A key like `"id"` would pass trivially even if it appeared only in a comment. The test does not exercise that these keys are in the function's return dict — only that they appear somewhere in the file. If the return shape were changed, this test would likely still pass.

**Fix:** Use the existing `_get_cases_source_lines()` helper to scope the assertion to the function body, consistent with the other three tests in the class:
```python
def test_get_cases_preserves_return_keys(self):
    lines = _get_cases_source_lines()
    assert lines, "Could not extract get_cases() body from api/services/cases.py"
    combined = "\n".join(lines)
    required_keys = [
        "id", "slug", "case_name", "docket_number", "term_year",
        "argued_date", "argument_id", "question_number",
    ]
    for key in required_keys:
        assert f'"{key}"' in combined or f"'{key}'" in combined, (
            f"get_cases() return dict must include key '{key}'"
        )
```

---

## Info

### IN-01: `_derive_slug` import marked `noqa: F401` but the symbol is used

**File:** `api/services/admin_arguments.py:26`

**Issue:** The import comment reads `# noqa: F401 — re-exported for tests`, implying the symbol is only needed for re-export. However, `_derive_slug` is also called at line 203 within `update_argument`, so the import is not unused at all. The `noqa` suppression is unnecessary and misleading — it suggests future maintainers should not remove the import only because tests import it, when in fact it is used directly.

**Fix:** Remove the `noqa: F401` comment, or update it to accurately document why it is present:
```python
from pipeline.commands.ingest import _derive_slug
```

---

### IN-02: `badgeStyle` and `badgeLabel` duplicated verbatim across two Svelte files

**File:** `app/src/routes/admin/arguments/+page.svelte:20–36` and `app/src/routes/admin/arguments/[id]/+page.svelte:25–41`

**Issue:** The `badgeStyle()` and `badgeLabel()` functions, plus the `formatDate()` function, are copy-pasted identically in both the list page and the detail page. If the badge color scheme or status logic changes, both files must be updated in sync. The list and detail pages are in the same route tree and could share a `+layout.svelte`-scoped helper or a small lib utility.

**Fix:** Extract to a shared module such as `app/src/lib/argumentBadge.ts`:
```typescript
export function badgeStyle(resolved_at: string | null, published_at: string | null): string { ... }
export function badgeLabel(resolved_at: string | null, published_at: string | null): string { ... }
export function formatDate(iso: string): string { ... }
```
Then import in both pages. (Note: the pipeline job page has its own inline `formatArgDate` — that can stay inline since it is a one-liner `const`.)

---

### IN-03: Pipeline job actions use global `fetch` instead of event `fetch`

**File:** `app/src/routes/admin/pipeline/[job_id]/+page.server.ts:112,150`

**Issue:** The `resolve` and `addPerson` action handlers destructure `{ request, params }` but not `fetch`. They call the global `fetch` for their FastAPI requests. Unlike the `load` function (CR-01, which is a BLOCKER), SvelteKit action handlers run entirely server-side in a request context where the global `fetch` is available and functional. However, the pattern is inconsistent with the rest of this codebase (the arguments detail page actions correctly destructure `fetch`), and using the event `fetch` would be more correct if SvelteKit's fetch ever adds tracing or forwarding in a future version.

**Fix:** Add `fetch` to each action's destructure:
```typescript
resolve: async ({ request, params, fetch }) => { ... }
addPerson: async ({ request, params, fetch }) => { ... }
```

---

_Reviewed: 2026-06-22_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
