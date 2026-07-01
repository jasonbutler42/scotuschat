---
phase: 21-admin-ui-surface
reviewed: 2026-07-01T00:00:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - api/routers/admin.py
  - api/services/admin_arguments.py
  - api/services/admin_jobs.py
  - api/tests/test_admin_arguments_service.py
  - api/tests/test_admin_jobs_service.py
  - app/src/lib/components/AdminSubNav.svelte
  - app/src/lib/components/TopNav.svelte
  - app/src/routes/admin/+layout.svelte
  - app/src/routes/admin/arguments/[id]/+page.server.ts
  - app/src/routes/admin/arguments/[id]/+page.svelte
  - app/src/routes/admin/pipeline/[job_id]/+page.server.ts
  - app/src/routes/admin/pipeline/[job_id]/+page.svelte
findings:
  critical: 4
  warning: 6
  info: 3
  total: 13
status: issues_found
---

# Phase 21: Code Review Report

**Reviewed:** 2026-07-01T00:00:00Z
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

This phase surfaces admin argument and pipeline-run management UIs and the
delete-run/delete-argument backend plumbing. The backend service layer is
solid overall — the FK-ordered cascade in `delete_argument`, the
`synchronize_session=False` guards on every bulk statement, and the atomic
rowcount-based step-advance pattern are all correctly implemented.

Four blockers were found: an unhandled exception that crashes the server when
`update_argument_metadata` receives a malformed date string; a client-side
polling loop that may silently fail if SvelteKit routes polling requests to the
page handler instead of the `+server.ts` API endpoint; a `TopNav` component
that declares only `'public'` as a valid variant type but the prop is never
read, making it dead code while the admin layout shows the public nav
(Cases/Admin links) to logged-in operators; and `aria-selected={false}`
hardcoded on all combobox options, permanently suppressing keyboard-highlight
state for screen readers.

Six warnings cover a missing `try/except` wrapper at the router level for
`update_argument_metadata`, silent empty-string storage for `source_docket`,
missing test coverage for three new service functions, ambiguous
`deleteSubmitting` reset timing, verbatim `error_message` display, and an
unusual `$effect` inside a Svelte action.

---

## Critical Issues

### CR-01: `update_argument_metadata` crashes on malformed argued_date — unhandled ValueError propagates as 500

**File:** `api/services/admin_arguments.py:533-536`

**Issue:** `datetime.date.fromisoformat(body.argued_date)` is called without a
`try/except`. If the operator submits a non-ISO string (e.g. a browser
auto-fill value like `"07/01/2026"`) the call raises `ValueError`. This
propagates to the router at `api/routers/admin.py:769-772`, which does **not**
wrap `update_argument_metadata` in a `try/except ValueError` — it only checks
`result is False`. The request produces an unhandled 500 instead of a 422.

Compare with the sibling `update_argument` service (line 262-266) which wraps
the same `fromisoformat` call correctly.

**Fix — service:**
```python
# api/services/admin_arguments.py
parsed_date: datetime.date | None = None
if body.argued_date:
    try:
        parsed_date = datetime.date.fromisoformat(body.argued_date)
    except ValueError:
        raise ValueError("invalid_date_format")
```

**Fix — router:**
```python
# api/routers/admin.py  update_argument_metadata handler
try:
    result = await arguments_service.update_argument_metadata(db, argument_id, body)
except ValueError as exc:
    raise HTTPException(status_code=422, detail=str(exc)) from exc
if result is False:
    raise HTTPException(status_code=404, detail="Argument not found")
return {"success": True}
```

---

### CR-02: Polling loop may silently parse HTML as JSON when SvelteKit routes to the page handler

**File:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte:73-83`

**Issue:** The polling effect sends:
```js
const res = await fetch(`/admin/pipeline/${liveJob.id}`, {
    headers: { Accept: 'application/json' },
});
```

When the `Accept: application/json` header is honored SvelteKit correctly routes
this to `+server.ts`, which returns the JSON `AdminJobResponse`. However, if
SvelteKit content-negotiation does not activate (misconfigured CDN, middleware
stripping headers, or a future SvelteKit version change), the request hits the
SSR page handler which returns HTML. The code then calls `res.json()` on that
HTML body, which throws, is caught by the empty `catch { return; }` block, and
silently skips the tick. Because the response status is 200 (not an error),
`if (!res.ok) return` does not fire either. The result is that the poll loop
runs continuously but never updates `liveJob` — the operator sees the spinner
indefinitely with no error.

**Fix:** Validate the `Content-Type` before parsing:
```js
if (!res.ok) return;
const ct = res.headers.get('content-type') ?? '';
if (!ct.includes('application/json')) {
    // Routing failure — content-negotiation did not activate
    console.error('[poll] expected JSON, got:', ct);
    return;
}
let fresh: typeof liveJob | null = null;
try {
    fresh = await res.json();
} catch {
    return;
}
```

---

### CR-03: `TopNav` renders public site navigation (Cases + Admin links) inside the admin shell, `variant` prop is dead code

**File:** `app/src/lib/components/TopNav.svelte:2` / `app/src/routes/admin/+layout.svelte:10`

**Issue:** `TopNav.svelte` declares `let { variant }: { variant: 'public' } = $props();`
but `variant` is never referenced in the template — the prop is a dead
declaration. The admin layout at `+layout.svelte:10` passes `variant="public"`
and the component unconditionally renders the Cases link (public-facing) and an
Admin link (pointing back to `/admin` while already on `/admin/*`). An operator
mid-task sees public navigation controls that take them off the admin surface.
This is an architectural correctness defect: the admin shell should not include
`/cases` and `/admin` links visible in every admin page header.

**Fix (minimal):** Add an `adminShell` boolean prop and suppress the public
links when truthy:
```svelte
<!-- TopNav.svelte -->
let { variant, adminShell = false }: { variant: 'public'; adminShell?: boolean } = $props();

{#if !adminShell}
<a href="/cases" ...>Cases</a>
<a href="/admin" ...>Admin</a>
{/if}
```
Then in `+layout.svelte`: `<TopNav variant="public" adminShell={true} />`

Alternatively, replace `TopNav` with `AdminSubNav` only in the admin layout
and remove `TopNav` from the admin shell entirely.

---

### CR-04: `aria-selected={false}` hardcoded on all combobox `<li>` options — keyboard highlight never communicated to screen readers

**File:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte:909` and line ~931

**Issue:** Every `<li role="option">` in the custom combobox listbox has
`aria-selected={false}` as a static literal. WAI-ARIA 1.2 requires that the
currently highlighted option carries `aria-selected="true"`. The
`s.comboHighlight` index drives background-color styling correctly but is never
wired to `aria-selected`. A screen reader user navigating with arrow keys will
always hear "not selected" for every item regardless of which is highlighted.

**Fix:**
```svelte
{#each filteredCandidates as candidate, idx (candidate.id)}
    <li
        role="option"
        aria-selected={s.comboHighlight === idx}
        ...
    >
```
And for the "Add new person" sentinel:
```svelte
<li
    role="option"
    aria-selected={s.comboHighlight === filteredCandidates.length}
    ...
>
```

---

## Warnings

### WR-01: `update_argument_metadata` stores empty string for `source_docket` when caller sends `""`

**File:** `api/services/admin_arguments.py:545-546`

**Issue:** The guard is `if body.source_docket is not None`, which passes empty
string `""` through and writes it to the database column. The SvelteKit action
at `+page.server.ts:337` converts an empty form field to `null`
(`trim() || null`), so the normal UI path is safe. But a direct API call with
`{"source_docket": ""}` stores an empty string rather than `NULL`. The existing
code comment ("WR-01: always writing source_docket=body.source_docket would NULL
an existing docket") acknowledges the null concern but does not address the
empty-string case.

**Fix:**
```python
if body.source_docket is not None and body.source_docket.strip() != "":
    values_to_set["source_docket"] = body.source_docket
```

---

### WR-02: No test coverage for `update_argument_metadata`, `check_duplicate_argument`, or `update_participant_side`

**File:** `api/tests/test_admin_arguments_service.py` (entire file)

**Issue:** Three service functions added in phases 15 and 19 have zero test
coverage — no import test, no structural guard, no DB-guarded behavioral test.
The structural guard `test_service_file_has_synchronize_session_false` (line
137-154) counts every `update()`/`delete()` call file-wide so new calls in
those functions inflate `stmt_count`, but their specific behaviors (including the
CR-01 date bug in `update_argument_metadata`) are not validated. The `update_argument`
service was similarly untested before the CR-01 date bug was introduced in the
`update_argument_metadata` refactor.

**Fix:** Add at minimum:
```python
def test_update_argument_metadata_importable() -> None:
    from api.services.admin_arguments import update_argument_metadata

def test_check_duplicate_argument_importable() -> None:
    from api.services.admin_arguments import check_duplicate_argument

def test_update_participant_side_importable() -> None:
    from api.services.admin_arguments import update_participant_side
```
Plus DB-guarded tests for `check_duplicate_argument` positive/negative cases.

---

### WR-03: Router does not wrap `update_argument_metadata` call in `try/except ValueError`

**File:** `api/routers/admin.py:769-772`

**Issue:** This is the router-side half of CR-01. Even after fixing the service
to raise `ValueError` on bad dates (CR-01 fix), the router handler must be
updated to catch it and convert to HTTPException 422. Currently the handler is:
```python
result = await arguments_service.update_argument_metadata(db, argument_id, body)
if result is False:
    raise HTTPException(status_code=404, detail="Argument not found")
return {"success": True}
```
Every other mutating endpoint in this router (`update_argument`, `publish_argument`,
`unpublish_argument`, `update_participant_side`, `merge_person`, etc.) wraps the
service call in `try/except ValueError`. This endpoint is the sole exception.
Listed separately from CR-01 since the service fix and router fix are independent
changes that could be missed independently.

**Fix:** Wrap the service call as shown in CR-01 fix.

---

### WR-04: `deleteSubmitting` reset in `use:enhance` callback may not run before navigation on success

**File:** `app/src/routes/admin/arguments/[id]/+page.svelte:481-488` / `app/src/routes/admin/pipeline/[job_id]/+page.svelte:1515-1520`

**Issue:** The delete Danger Zone form sets `deleteSubmitting = true` on submit
and resets it in the `enhance` callback:
```js
use:enhance={() => {
    deleteSubmitting = true;
    return async ({ update }) => {
        deleteSubmitting = false;
        await update();
    };
}}
```
On a **successful** delete, the server action calls `throw redirect(303, ...)`.
SvelteKit navigates away; whether the callback fires before the component
unmounts is not guaranteed. If navigation completes first, `deleteSubmitting`
is never reset — cosmetically harmless since the component unmounts, but it
leaves the button in a disabled state visible for a flash before navigation.
More importantly, if a future refactor changes the success path to return data
instead of redirecting, the pattern would leave the button permanently disabled.

**Fix:**
```js
return async ({ update }) => {
    deleteSubmitting = false;  // always reset before update
    await update();
};
```

---

### WR-05: `liveJob.error_message` rendered verbatim in monospace block — pipeline path data may leak

**File:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte:1419-1426`

**Issue:** `error_message` from pipeline subprocess stderr is displayed without
any truncation or sanitization (Svelte's template escaping prevents XSS).
Subprocess error messages frequently include full file system paths (e.g.
`FileNotFoundError: [Errno 2] No such file or directory: '/data/uploads/42.pdf'`).
While this endpoint is admin-only, it reveals server-side file paths to anyone
with the admin token. This is a mild information disclosure but noteworthy for
an operator-facing surface.

**Fix:** Truncate long messages or strip path-like substrings before display:
```svelte
{liveJob.error_message?.length > 500
  ? liveJob.error_message.slice(0, 500) + '…'
  : liveJob.error_message}
```

---

### WR-06: `comboOutsideClick` Svelte action contains `$effect` — causes double event listener registration

**File:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte:373-393`

**Issue:** The action body calls `$effect(...)` internally, which is not a
standard Svelte action pattern. Svelte actions (used via `use:`) are expected
to return a `{ destroy() }` object; placing `$effect` inside creates a nested
reactive context that executes during component initialization. The result is
that `handleClick` is registered twice — once via the `$effect` (line 384) and
once conceptually through the action's mounting. The `destroy()` method removes
only one registration (the one created by the `$effect`). In practice only one
listener fires (the DOM deduplicates identical listener + function reference
pairs), but the pattern is fragile and relies on undocumented Svelte internals.

**Fix:** Remove the `$effect` and register directly:
```js
function comboOutsideClick(container: HTMLElement, rowKey: string) {
    function handleClick(e: MouseEvent) {
        if (!container.contains(e.target as Node)) {
            const s = rowStates[rowKey];
            if (s) s.comboOpen = false;
        }
    }
    document.addEventListener('click', handleClick);
    return {
        destroy() {
            document.removeEventListener('click', handleClick);
        }
    };
}
```

---

## Info

### IN-01: `variant` prop in `TopNav` is declared but never read — dead prop declaration

**File:** `app/src/lib/components/TopNav.svelte:2`

**Issue:** `let { variant }: { variant: 'public' } = $props()` destructures
`variant` but the variable is never used in the template. TypeScript does not
warn because destructuring itself counts as usage. The prop is vestigial.

**Fix:** Remove the prop (as part of the CR-03 fix) or add a `@ts-expect-error`
comment documenting why it is declared but unused if intentionally reserved for
future use.

---

### IN-02: Source-scanning structural guard may over-count `update(` occurrences in docstrings

**File:** `api/tests/test_admin_arguments_service.py:146-154`

**Issue:** `re.findall(r'\b(update|delete)\(', source)` matches the substring
anywhere in the file text, including in docstrings and comments. The current
`admin_arguments.py` docstrings contain phrases like "update() statement" which
happen to not match the regex (the regex requires an identifier word boundary
before `update`). However, future edits to docstrings or comments that include
`update(` or `delete(` patterns would falsely inflate `stmt_count`, causing the
assertion to require more `synchronize_session=False` guards than the code
actually has.

**Fix:** Strip string literals before scanning, or use `ast.parse` to walk
only function bodies:
```python
import ast
tree = ast.parse(source)
# walk Call nodes only inside FunctionDef bodies
```

---

### IN-03: `console.debug` fires on every poll tick in production

**File:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte:87`

**Issue:**
```js
console.debug('[poll]', { status: liveJob.status, current_step: liveJob.current_step });
```
This fires every 1 second while a job is running. In Chromium DevTools `console.debug`
is suppressed at the default log level, but the call still allocates the argument
object on every tick. In Firefox and some log aggregators `console.debug` is
visible by default.

**Fix:**
```js
if (import.meta.env.DEV) {
    console.debug('[poll]', { status: liveJob.status, current_step: liveJob.current_step });
}
```

---

_Reviewed: 2026-07-01T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
