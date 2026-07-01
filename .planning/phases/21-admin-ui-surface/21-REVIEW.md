---
phase: 21-admin-ui-surface
reviewed: 2026-07-01T00:00:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - api/services/admin_arguments.py
  - api/tests/test_admin_arguments_service.py
  - api/routers/admin.py
  - app/src/routes/admin/arguments/[id]/+page.server.ts
  - app/src/routes/admin/arguments/[id]/+page.svelte
  - api/tests/test_admin_jobs_service.py
  - api/services/admin_jobs.py
  - app/src/routes/admin/pipeline/[job_id]/+page.server.ts
  - app/src/routes/admin/pipeline/[job_id]/+page.svelte
  - app/src/lib/components/AdminSubNav.svelte
  - app/src/routes/admin/+layout.svelte
  - app/src/lib/components/TopNav.svelte
findings:
  critical: 4
  warning: 7
  info: 3
  total: 14
status: issues_found
---

# Phase 21: Code Review Report

**Reviewed:** 2026-07-01T00:00:00Z
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Phase 21 adds two delete flows (argument delete, job/run delete), a polling-based pipeline detail view, the argument detail editor with participant role assignment, and three nav components. The backend service logic is generally sound and the FK-ordered cascade in `delete_argument` is correctly implemented. The most serious defects are a logic bug that silently blocks all published-argument deletes via the wrong status check, an open-redirect / SSRF vector in the photo-URL fetch endpoint, a client-side polling loop fetching the wrong URL shape, and a condition bug in `update_argument_metadata` that can write a NULL date when the operator clears a date field.

---

## Critical Issues

### CR-01: `delete_argument` checks `status == PUBLISHED` but published arguments use `published_at`, not necessarily `status`

**File:** `api/services/admin_arguments.py:463`
**Issue:** The guard `if argument.status == ArgumentStatusEnum.PUBLISHED: return False` blocks deletion only when the ORM status column equals `PUBLISHED`. However, `publish_argument` stamps `published_at` via a Core `UPDATE` with `synchronize_session=False`, which **does not update the in-session ORM object**. The in-memory `argument.status` loaded on line 459 still reflects the value from the `SELECT` issued on line 458. If `status` and `published_at` can drift (e.g. `published_at` is set but `status` is still `DRAFT` because a migration or manual fix put the rows out of sync), the guard would pass and allow deletion of a published argument. More critically, the symmetry is backwards: `publish_argument` only sets `published_at`; it does **not** change `status`. The status column tracks pipeline state (`PIPELINE → DRAFT → PUBLISHED`) — verify that `publish_argument` actually transitions `status` to `PUBLISHED`. If it does not, then a published argument (one with `published_at IS NOT NULL`) whose `status` column is still `DRAFT` will pass the guard on line 463 and be deletable. The router docstring says "Returns 409 if `argument.status == 'published'`" but the real safety net should be `published_at IS NOT NULL`.

**Fix:** Guard on `published_at` instead of (or in addition to) `status`, since `published_at` is the authoritative stamp:
```python
# In delete_argument, after loading the argument row:
if argument.published_at is not None:
    return False
```
Additionally, confirm that `publish_argument` transitions `argument.status` to `PUBLISHED` atomically with the `published_at` stamp, so both checks are consistent.

---

### CR-02: `update_argument_metadata` condition bug — always writes `argued_date` even when input is empty/None

**File:** `api/services/admin_arguments.py:540`
**Issue:** The condition for including `argued_date` in the update is:
```python
if body.argued_date is not None or parsed_date is not None:
    values_to_set["argued_date"] = parsed_date
```
`parsed_date` is set to `None` when `body.argued_date` is falsy (empty string or `None`) on lines 531–534:
```python
parsed_date: datetime.date | None = (
    datetime.date.fromisoformat(body.argued_date)
    if body.argued_date
    else None
)
```
The condition `body.argued_date is not None or parsed_date is not None` evaluates `True` when `body.argued_date` is a non-None value — including an **empty string `""`**. An empty string passes `is not None`, so `parsed_date` is `None` (the `if body.argued_date` branch is falsy for `""`), and the UPDATE writes `argued_date = NULL`. This silently NULLs the argued_date whenever the operator submits the saveMetadata form with an empty date field.

The comment on line 537 ("WR-01: always writing source_docket=body.source_docket would NULL an existing docket...") shows the author recognized this same problem for `source_docket` but did not apply the same protection to `argued_date`.

**Fix:** Only include `argued_date` in the update dict when `body.argued_date` is a non-empty, non-None string (i.e. when `parsed_date` is actually a date):
```python
if parsed_date is not None:
    values_to_set["argued_date"] = parsed_date
```

---

### CR-03: Client-side polling fetches the page URL, not a data-only endpoint — may trigger HTML response or infinite state loop

**File:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte:74`
**Issue:** The polling effect fetches:
```javascript
const res = await fetch(`/admin/pipeline/${liveJob.id}`, {
    headers: { Accept: 'application/json' },
});
```
This sends a request to the SvelteKit page route (`/admin/pipeline/[job_id]`), not to the FastAPI job endpoint (`/api/admin/jobs/{job_id}`). SvelteKit page routes respond with HTML by default; although `Accept: application/json` triggers SvelteKit's data-only response mode (returns the `+page.server.ts` load data as JSON), this is an undocumented internal behaviour that depends on SvelteKit version and whether the page has a `+page.server.ts` load function. The load function at `+page.server.ts:28-109` makes **four nested HTTP calls** on every poll (jobs, people, participants, argument) — running this once per second is extremely wasteful and compounds latency. More critically, the load function also triggers the `GET /api/admin/jobs/{job_id}` **step-advance side effect** in `admin.py:298-316`, meaning the step-advance fires from the poll. While the step-advance is idempotent (rowcount guard), this is unintended coupling.

If the SvelteKit JSON data-response fails (wrong Content-Type, wrong shape), `fresh = await res.json()` at line 79 would throw and the `if (!res.ok) return` guard at line 77 would not protect against it since `res.ok` could still be true.

**Fix:** Poll the FastAPI endpoint directly from the server action, or add a dedicated lightweight `+server.ts` endpoint. If the current approach is kept, add a `try/catch` around the JSON parse:
```javascript
let fresh: Job | null = null;
try {
    fresh = await res.json();
} catch {
    return; // malformed response — skip this tick
}
if (!fresh) return;
```
The four-request fan-out in the load function per poll tick is a design concern that should be addressed with a dedicated lightweight poll endpoint.

---

### CR-04: `upload_person_photo` URL path — operator-supplied URL fetched server-side without allowlist (SSRF)

**File:** `api/routers/admin.py:536-541`
**Issue:** The `photo_url` parameter in `POST /api/admin/people/{person_id}/photo` is fetched directly by the server:
```python
async with httpx.AsyncClient(timeout=10.0) as client:
    r = await client.get(photo_url, follow_redirects=True)
```
There is no scheme enforcement, no hostname allowlist, and `follow_redirects=True` is enabled. An operator (or anyone with the admin token) can supply `http://169.254.169.254/latest/meta-data/` (AWS metadata endpoint), `http://localhost:5432/` (internal Postgres), or any other internal network address. While this is an admin-only endpoint, the CLAUDE.md constraint set mentions PCI DSS and CWE-918 is applicable. The comment says "Auth inherited from router-level dependency" but that does not address SSRF. Note that `_validate_pdf_url` exists for the PDF URL path but no equivalent function guards the photo URL.

**Fix:** Enforce `https` scheme and optionally restrict to known image CDN hosts, or at minimum reject private/loopback IP ranges before fetching. At minimum:
```python
from urllib.parse import urlparse

parsed = urlparse(photo_url)
if parsed.scheme != 'https':
    raise HTTPException(status_code=422, detail="Photo URL must use HTTPS.")
```
Disable `follow_redirects` or limit redirect depth to avoid redirect-based SSRF bypass.

---

## Warnings

### WR-01: `test_service_file_has_synchronize_session_false` — structural guard counts `update(Argument)` calls only, misses `delete()` and `update(AdminJob)` calls in the same file

**File:** `api/tests/test_admin_arguments_service.py:147-153`
**Issue:** The test counts `source.count("update(Argument)")` and compares against `source.count("synchronize_session=False")`. The service file now contains `update(ArgumentParticipant)`, `update(AdminJob)`, `delete(Utterance)`, `delete(PipelineRun)`, etc. — all of which also require the guard. The count of `update(Argument)` occurrences (which is 4) will be less than the total `synchronize_session=False` count (which is more), so the assertion passes, but it does not actually verify that every non-`Argument` update/delete also has the guard. This is a false sense of security.

**Fix:** Count all `update(` and `delete(` calls rather than only `update(Argument)`:
```python
update_count = source.count(".execution_options") - 0  # already present
# Or count all update() + delete() calls:
import re
stmt_count = len(re.findall(r'\b(update|delete)\(', source))
sync_false_count = source.count("synchronize_session=False")
assert sync_false_count >= stmt_count
```

---

### WR-02: `update_argument` — `ValueError` from `datetime.date.fromisoformat()` leaks the raw exception message to the HTTP client

**File:** `api/services/admin_arguments.py:263` and `api/routers/admin.py:700-703`
**Issue:** `body.argued_date` is parsed with `datetime.date.fromisoformat(body.argued_date)` without a try/except in the service. The router catches `ValueError` generically:
```python
except ValueError as exc:
    raise HTTPException(status_code=422, detail=str(exc)) from exc
```
Python's `fromisoformat` raises `ValueError: Invalid isoformat string: '...'` which includes the raw user-supplied string in the exception message, and that string is echoed back verbatim in the 422 detail. While this is a minor information disclosure (the operator typed the value themselves), it is inconsistent with the project pattern of using controlled error strings (`"slug_collision"`, `"docket_collision"`). A future change where `argued_date` comes from a different source could leak unexpected content.

**Fix:** Wrap the parse in the service with a controlled message:
```python
if body.argued_date is not None:
    try:
        argument.argued_date = datetime.date.fromisoformat(body.argued_date)
    except ValueError:
        raise ValueError("invalid_date_format")
```

---

### WR-03: `+page.server.ts` (pipeline detail) — `approve` action fetches the job a second time to get `argument_id`, creating a TOCTOU window

**File:** `app/src/routes/admin/pipeline/[job_id]/+page.server.ts:170-180`
**Issue:** The `approve` action fetches `/api/admin/jobs/{job_id}` to retrieve `argument_id`, then uses that `argument_id` to PATCH participant sides. Between the fetch and the PATCH, the job could have been deleted or its `argument_id` could have changed. If the fetch fails (non-OK), the code silently continues (`// Continue — PATCH is best-effort`) and calls `/api/admin/jobs/{job_id}/approve` regardless, which may approve a job with no `argument_id`.

```typescript
} catch {
    // Continue — PATCH is best-effort; approve still proceeds
}
```

The approve endpoint itself will raise a 422 if `argument_id` is None, but the silent swallow of the job-fetch failure hides the real problem and makes debugging difficult.

**Fix:** If the job fetch fails, return `fail(502, { approveError: 'Could not load job. Try again.' })` rather than silently continuing. The PATCH of participant sides should be clearly documented as best-effort separately from the approve call.

---

### WR-04: `+layout.svelte` — renders `TopNav` with `variant="public"` for all admin pages, including admin-only pages

**File:** `app/src/routes/admin/+layout.svelte:10`
**Issue:** The layout always renders `<TopNav variant="public" />` (which shows the "Cases" and "Admin" links from the public site nav) followed by `<AdminSubNav />` (which shows pipeline/arguments/people links). The public nav's "Admin" link on the admin-side pages is a dead self-link that provides no value and may confuse operators. More importantly, the `TopNav` component prop type is `{ variant: 'public' }` (only one valid value), meaning the component was designed for public pages and is being reused here without an admin-specific variant.

This is not a security issue (the page is already behind auth), but it is a quality defect — the admin layout renders two nav bars (one public, one admin-specific) which is redundant. The admin subnav alone is sufficient.

**Fix:** Remove the `<TopNav variant="public" />` line from `+layout.svelte`, or add an `admin` variant to `TopNav` that hides the "Admin" self-link.

---

### WR-05: `delete_argument` — `status == PUBLISHED` check diverges from `unpublish_argument` which checks `published_at`

**File:** `api/services/admin_arguments.py:463` vs `api/services/admin_arguments.py:402`
**Issue:** `delete_argument` guards with `argument.status == ArgumentStatusEnum.PUBLISHED` while `unpublish_argument` guards with `argument.published_at is None`. These two checks are not equivalent and can diverge if status and published_at drift. (This is related to CR-01 but is a distinct observation: the inconsistency between the two functions' guards creates a maintenance hazard even if the current data is always consistent.) If `published_at` is set but `status` is still `DRAFT`, `delete_argument` would allow deletion while `unpublish_argument` would correctly see the argument as published.

**Fix:** Standardize all publish-state checks on `published_at` across both functions, consistent with how `publish_argument` works.

---

### WR-06: `+page.svelte` (argument detail) — `select` element uses `value={participant.side}` but Svelte 5 `<select>` controlled value requires `bind:value` or `selected` attribute on `<option>`

**File:** `app/src/routes/admin/arguments/[id]/+page.svelte:312-329`
**Issue:** The advocate role `<select>` is rendered as:
```svelte
<select name="side" value={participant.side} ...>
    <option value="PETITIONER">...</option>
    ...
</select>
```
In Svelte 5, the `value` attribute on `<select>` does not control which option is selected — it sets the element's `value` DOM property on initial render but does not reactively update the selected option when the data changes, nor does it pre-select the correct option after a form error re-render. The correct Svelte 5 approach is to use `bind:value` (for reactive two-way binding) or mark the matching `<option>` with `selected={participant.side === 'PETITIONER'}`. Without this, the select always defaults to the first option (`PETITIONER`) rather than showing the participant's current side.

**Fix:** Either add `bind:value` (requires a mutable `$state` variable per participant) or set `selected` on each option:
```svelte
<option value="PETITIONER" selected={participant.side === 'PETITIONER'}>Petitioner's Counsel</option>
<option value="RESPONDENT" selected={participant.side === 'RESPONDENT'}>Respondent's Counsel</option>
<option value="AMICUS" selected={participant.side === 'AMICUS'}>Amicus Curiae</option>
<option value="UNKNOWN" selected={participant.side === 'UNKNOWN'}>Counsel</option>
```

---

### WR-07: `get_argument_detail` — N+1 query in tenure gap check issues one EXISTS subquery per bench participant

**File:** `api/services/admin_arguments.py:143-165`
**Issue:** For each bench participant (could be 9 Justices), the code issues an individual EXISTS query:
```python
for person_id, full_name in bench_rows:
    covering = exists(select(CourtTenure.id).where(...))
    has_covering = (await db.execute(select(covering))).scalar()
```
This is O(n) round-trips to the database where n is the number of bench participants. While performance is out of v1 scope per the review instructions, this pattern will raise a correctness issue if the database session is under transaction pressure from concurrent writes — each sequential await is a separate round-trip through PgBouncer's transaction-mode pooling, and the session may not see its own prior uncommitted data consistently across the loop. The bigger issue is that a missing `CourtTenure` for a newly-added Justice could silently produce spurious warnings if the tenure rows were not yet committed when this path executes.

This is flagged as WARNING rather than BLOCKER because the query is correct in isolation; it only degrades under concurrent write load.

**Fix:** Consolidate into a single query that LEFT JOINs `CourtTenure` and uses an aggregate to identify gaps, eliminating the N+1 pattern.

---

## Info

### IN-01: `admin_arguments.py` — `_derive_slug` imported with `# noqa: F401 — re-exported for tests` but this re-export pattern is fragile

**File:** `api/services/admin_arguments.py:38`
**Issue:** `_derive_slug` is imported from `pipeline.commands.ingest` and re-exported for tests via the `noqa` comment. This creates an implicit API surface for the tests. If the import is removed during a refactor (it's only used locally within the module), the tests will break without a clear error message since they import from the service, not from the pipeline directly.

**Fix:** Export `_derive_slug` from `pipeline/commands/ingest.py` as a public symbol (`derive_slug` without leading underscore), and have the tests import it from there directly. This removes the service-layer re-export and makes the dependency explicit.

---

### IN-02: `+layout.svelte` — `page.url.pathname !== '/admin/login'` comparison is fragile and duplicates route logic

**File:** `app/src/routes/admin/+layout.svelte:9`
**Issue:** The nav visibility is gated by a hardcoded string comparison against the URL pathname. If the login route is ever renamed or moved, this check will silently break — the nav will render on the login page (leaking the admin subnav before authentication). SvelteKit provides `$page.route.id` for route-based conditional logic which is more robust than pathname matching.

**Fix:** Use `$page.route.id` rather than `$page.url.pathname`:
```svelte
{#if page.route.id !== '/admin/login'}
```
Or better: move the login page outside the admin layout entirely so no conditional is needed.

---

### IN-03: `AdminSubNav.svelte` — logout button POSTs to `/admin?/logout` but no `logout` action is visible in the reviewed files

**File:** `app/src/lib/components/AdminSubNav.svelte:26`
**Issue:** The logout button posts to `/admin?/logout`. No `logout` action was found in the reviewed files (the admin layout `+layout.svelte` has no `<script>` block with server-side actions, and `+layout.server.ts` was not in the file list). If this action does not exist, the logout button silently fails (SvelteKit returns a 404 action error, not a user-visible message). The button provides no visual feedback on failure.

**Fix:** Confirm that `src/routes/admin/+layout.server.ts` exports a `logout` action. If the action exists, add a `use:enhance` callback to the logout form to handle failures gracefully.

---

_Reviewed: 2026-07-01T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
